from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models
class VolunteerForm(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    phone: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VolunteerFormCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    message: Optional[str] = None

class ShelterSearchRequest(BaseModel):
    lat: float
    lon: float
    radius: int = 50000  # Default 50km radius
    services: Optional[List[str]] = None
    pet_friendly: Optional[bool] = None

class Shelter(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    capacity: Optional[int] = None
    services: List[str] = []
    pet_friendly: bool = False
    description: Optional[str] = None

class Organization(BaseModel):
    name: str
    description: str
    website: str
    donation_link: str

# Overpass API Integration
async def query_overpass_api(lat: float, lon: float, radius: int) -> List[dict]:
    """
    Query OpenStreetMap Overpass API for shelters and warming centers.
    """
    # Overpass API query for shelters, social facilities, and emergency warming centers
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="shelter"](around:{radius},{lat},{lon});
      node["amenity"="social_facility"](around:{radius},{lat},{lon});
      node["social_facility"="shelter"](around:{radius},{lat},{lon});
      node["social_facility"="homeless_shelter"](around:{radius},{lat},{lon});
      node["emergency"="warming_center"](around:{radius},{lat},{lon});
      way["amenity"="shelter"](around:{radius},{lat},{lon});
      way["amenity"="social_facility"](around:{radius},{lat},{lon});
      way["social_facility"="shelter"](around:{radius},{lat},{lon});
      way["social_facility"="homeless_shelter"](around:{radius},{lat},{lon});
      way["emergency"="warming_center"](around:{radius},{lat},{lon});
    );
    out center body;
    """
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(overpass_url, data={'data': overpass_query})
            response.raise_for_status()
            data = response.json()
            return data.get('elements', [])
    except Exception as e:
        logger.error(f"Error querying Overpass API: {e}")
        raise HTTPException(status_code=500, detail="Error fetching shelter data")

def parse_shelter_data(element: dict) -> Shelter:
    """
    Parse OpenStreetMap element data into a Shelter object.
    """
    tags = element.get('tags', {})
    
    # Get coordinates
    if element['type'] == 'node':
        lat = element['lat']
        lon = element['lon']
    elif 'center' in element:
        lat = element['center']['lat']
        lon = element['center']['lon']
    else:
        lat = element.get('lat', 0)
        lon = element.get('lon', 0)
    
    # Extract name
    name = tags.get('name', tags.get('operator', 'Unnamed Shelter'))
    
    # Extract address components
    address_parts = []
    if tags.get('addr:housenumber'):
        address_parts.append(tags['addr:housenumber'])
    if tags.get('addr:street'):
        address_parts.append(tags['addr:street'])
    address = ' '.join(address_parts) if address_parts else None
    
    city = tags.get('addr:city')
    state = tags.get('addr:state')
    
    # Extract services
    services = []
    if tags.get('shelter_type'):
        services.append(f"Type: {tags['shelter_type']}")
    if tags.get('social_facility:for'):
        services.append(f"For: {tags['social_facility:for']}")
    if tags.get('wheelchair') == 'yes':
        services.append('Wheelchair accessible')
    if tags.get('internet_access') == 'yes':
        services.append('Internet access')
    if tags.get('healthcare'):
        services.append('Healthcare services')
    if tags.get('toilets') == 'yes':
        services.append('Restrooms')
    if tags.get('shower') == 'yes':
        services.append('Showers')
    if tags.get('laundry') == 'yes':
        services.append('Laundry')
    if tags.get('clothes') == 'yes':
        services.append('Clothing assistance')
    if tags.get('food') == 'yes' or tags.get('food_service'):
        services.append('Meals provided')
    
    # Pet friendly check
    pet_friendly = tags.get('animal_shelter') == 'yes' or tags.get('pets') == 'yes'
    
    # Capacity
    capacity = None
    if tags.get('capacity'):
        try:
            capacity = int(tags['capacity'])
        except ValueError:
            pass
    
    return Shelter(
        id=str(element['id']),
        name=name,
        lat=lat,
        lon=lon,
        address=address,
        city=city,
        state=state,
        phone=tags.get('phone'),
        website=tags.get('website') or tags.get('contact:website'),
        capacity=capacity,
        services=services,
        pet_friendly=pet_friendly,
        description=tags.get('description')
    )

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Warm Wishes API"}

@api_router.post("/shelters/search", response_model=List[Shelter])
async def search_shelters(search_request: ShelterSearchRequest):
    """
    Search for shelters near a given location using OpenStreetMap data.
    """
    try:
        elements = await query_overpass_api(
            search_request.lat,
            search_request.lon,
            search_request.radius
        )
        
        shelters = []
        for element in elements:
            try:
                shelter = parse_shelter_data(element)
                
                # Apply filters
                if search_request.pet_friendly is not None:
                    if shelter.pet_friendly != search_request.pet_friendly:
                        continue
                
                if search_request.services:
                    # Check if shelter has any of the requested services
                    shelter_services_lower = [s.lower() for s in shelter.services]
                    requested_services_lower = [s.lower() for s in search_request.services]
                    has_service = any(
                        any(req in shelter_serv for req in requested_services_lower)
                        for shelter_serv in shelter_services_lower
                    )
                    if not has_service:
                        continue
                
                shelters.append(shelter)
            except Exception as e:
                logger.error(f"Error parsing shelter data: {e}")
                continue
        
        logger.info(f"Found {len(shelters)} shelters")
        return shelters
        
    except Exception as e:
        logger.error(f"Error searching shelters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/volunteer", response_model=VolunteerForm)
async def submit_volunteer_form(form_data: VolunteerFormCreate):
    """
    Submit volunteer interest form.
    """
    try:
        volunteer_obj = VolunteerForm(**form_data.model_dump())
        
        doc = volunteer_obj.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        
        await db.volunteers.insert_one(doc)
        
        logger.info(f"Volunteer form submitted: {volunteer_obj.email}")
        return volunteer_obj
        
    except Exception as e:
        logger.error(f"Error submitting volunteer form: {e}")
        raise HTTPException(status_code=500, detail="Error submitting form")

@api_router.get("/organizations", response_model=List[Organization])
async def get_organizations():
    """
    Get list of organizations for donations.
    """
    # Static list of reputable organizations
    organizations = [
        Organization(
            name="National Coalition for the Homeless",
            description="Works to end and prevent homelessness through public education, policy advocacy, and grassroots organizing.",
            website="https://nationalhomeless.org",
            donation_link="https://nationalhomeless.org/donate"
        ),
        Organization(
            name="Coalition for the Homeless",
            description="The nation's oldest advocacy and direct service organization helping homeless men, women, and children.",
            website="https://www.coalitionforthehomeless.org",
            donation_link="https://www.coalitionforthehomeless.org/donate"
        ),
        Organization(
            name="National Alliance to End Homelessness",
            description="A leading voice on homelessness with a mission to prevent and end homelessness in the United States.",
            website="https://endhomelessness.org",
            donation_link="https://endhomelessness.org/donate"
        ),
        Organization(
            name="Salvation Army",
            description="Provides shelter, food, and support services to those experiencing homelessness across the country.",
            website="https://www.salvationarmyusa.org",
            donation_link="https://www.salvationarmyusa.org/usn/ways-to-give"
        )
    ]
    
    return organizations

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
