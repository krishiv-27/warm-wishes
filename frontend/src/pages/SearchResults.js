import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { ArrowLeft, Filter, MapPin, Phone, Globe, Users2, Heart, Navigation } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Checkbox } from '../components/ui/checkbox';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Fix Leaflet default marker icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Custom marker icon
const customIcon = new L.Icon({
  iconUrl: 'data:image/svg+xml;base64,' + btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f59e0b" stroke="#ffffff" stroke-width="1">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
    </svg>
  `),
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
});

const MapUpdater = ({ center }) => {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, 12);
    }
  }, [center, map]);
  return null;
};

const SearchResults = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [shelters, setShelters] = useState([]);
  const [filteredShelters, setFilteredShelters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [center, setCenter] = useState([39.8283, -98.5795]);
  const [filters, setFilters] = useState({
    petFriendly: false,
    meals: false,
    showers: false,
    healthcare: false,
  });
  const [selectedShelter, setSelectedShelter] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    const lat = searchParams.get('lat');
    const lon = searchParams.get('lon');
    const location = searchParams.get('location');

    if (lat && lon) {
      setCenter([parseFloat(lat), parseFloat(lon)]);
      searchShelters(parseFloat(lat), parseFloat(lon));
    } else if (location) {
      geocodeLocation(location);
    }
  }, [searchParams]);

  useEffect(() => {
    applyFilters();
  }, [filters, shelters]);

  const geocodeLocation = async (location) => {
    try {
      setLoading(true);
      const response = await axios.get(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(location)}&countrycodes=us&limit=1`
      );

      if (response.data && response.data.length > 0) {
        const { lat, lon } = response.data[0];
        setCenter([parseFloat(lat), parseFloat(lon)]);
        await searchShelters(parseFloat(lat), parseFloat(lon));
      } else {
        toast.error('Location not found. Please try a different search.');
        setLoading(false);
      }
    } catch (error) {
      console.error('Geocoding error:', error);
      toast.error('Error finding location');
      setLoading(false);
    }
  };

  const searchShelters = async (lat, lon) => {
    try {
      setLoading(true);
      const response = await axios.post(`${BACKEND_URL}/api/shelters/search`, {
        lat,
        lon,
        radius: 50000,
      });

      setShelters(response.data);
      setFilteredShelters(response.data);
      
      if (response.data.length === 0) {
        toast.info('No shelters found in this area. Try expanding your search.');
      }
    } catch (error) {
      console.error('Error searching shelters:', error);
      toast.error('Error loading shelter data');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...shelters];

    if (filters.petFriendly) {
      filtered = filtered.filter(s => s.pet_friendly);
    }

    if (filters.meals) {
      filtered = filtered.filter(s => 
        s.services.some(service => service.toLowerCase().includes('meal') || service.toLowerCase().includes('food'))
      );
    }

    if (filters.showers) {
      filtered = filtered.filter(s => 
        s.services.some(service => service.toLowerCase().includes('shower'))
      );
    }

    if (filters.healthcare) {
      filtered = filtered.filter(s => 
        s.services.some(service => service.toLowerCase().includes('healthcare'))
      );
    }

    setFilteredShelters(filtered);
  };

  const getDirections = (lat, lon) => {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    if (isMobile) {
      window.open(`https://maps.google.com/?daddr=${lat},${lon}`, '_blank');
    } else {
      window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`, '_blank');
    }
  };

  return (
    <div className="min-h-screen bg-midnight" data-testid="search-results-page">
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="text-white hover:text-hearth hover:bg-white/10"
            data-testid="back-to-home-button"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Back to Home
          </Button>
          
          <h1 className="text-xl md:text-2xl font-bold text-white font-playfair">
            Warm Wishes
          </h1>
          
          <Button
            variant="ghost"
            onClick={() => setShowFilters(!showFilters)}
            className="text-white hover:text-hearth hover:bg-white/10 md:hidden"
            data-testid="toggle-filters-button"
          >
            <Filter className="w-5 h-5" />
          </Button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 h-[calc(100vh-73px)]">
        <div className="lg:col-span-1 bg-slate-900 border-r border-slate-700 overflow-y-auto" data-testid="shelter-list-panel">
          <div className={`p-4 border-b border-slate-700 ${showFilters ? 'block' : 'hidden md:block'}`}>
            <h3 className="text-lg font-bold text-white mb-4 font-playfair flex items-center">
              <Filter className="w-5 h-5 mr-2 text-hearth" />
              Filters
            </h3>
            
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="pet-friendly"
                  checked={filters.petFriendly}
                  onCheckedChange={(checked) => setFilters({ ...filters, petFriendly: checked })}
                  data-testid="filter-pet-friendly"
                />
                <Label htmlFor="pet-friendly" className="text-slate-200 cursor-pointer">
                  Pet Friendly
                </Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="meals"
                  checked={filters.meals}
                  onCheckedChange={(checked) => setFilters({ ...filters, meals: checked })}
                  data-testid="filter-meals"
                />
                <Label htmlFor="meals" className="text-slate-200 cursor-pointer">
                  Meals Provided
                </Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="showers"
                  checked={filters.showers}
                  onCheckedChange={(checked) => setFilters({ ...filters, showers: checked })}
                  data-testid="filter-showers"
                />
                <Label htmlFor="showers" className="text-slate-200 cursor-pointer">
                  Showers Available
                </Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="healthcare"
                  checked={filters.healthcare}
                  onCheckedChange={(checked) => setFilters({ ...filters, healthcare: checked })}
                  data-testid="filter-healthcare"
                />
                <Label htmlFor="healthcare" className="text-slate-200 cursor-pointer">
                  Healthcare Services
                </Label>
              </div>
            </div>
          </div>

          <div className="p-4 border-b border-slate-700">
            <p className="text-slate-300 font-manrope" data-testid="results-count">
              {loading ? 'Searching...' : `${filteredShelters.length} ${filteredShelters.length === 1 ? 'shelter' : 'shelters'} found`}
            </p>
          </div>

          <div className="divide-y divide-slate-700">
            {filteredShelters.map((shelter) => (
              <div
                key={shelter.id}
                className={`p-4 cursor-pointer hover:bg-slate-800 transition-colors ${
                  selectedShelter?.id === shelter.id ? 'bg-slate-800 border-l-4 border-hearth' : ''
                }`}
                onClick={() => setSelectedShelter(shelter)}
                data-testid={`shelter-card-${shelter.id}`}
              >
                <h4 className="text-white font-bold mb-2 font-playfair">{shelter.name}</h4>
                
                {shelter.address && (
                  <p className="text-slate-300 text-sm mb-2 font-manrope flex items-start">
                    <MapPin className="w-4 h-4 mr-1 mt-0.5 flex-shrink-0" />
                    {shelter.address}
                    {shelter.city && `, ${shelter.city}`}
                    {shelter.state && `, ${shelter.state}`}
                  </p>
                )}

                {shelter.capacity && (
                  <p className="text-slate-400 text-sm mb-2 flex items-center">
                    <Users2 className="w-4 h-4 mr-1" />
                    Capacity: {shelter.capacity}
                  </p>
                )}

                {shelter.pet_friendly && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-pine/20 text-pine mr-2">
                    <Heart className="w-3 h-3 mr-1" />
                    Pet Friendly
                  </span>
                )}

                {shelter.services.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {shelter.services.slice(0, 3).map((service, idx) => (
                      <span key={idx} className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded">
                        {service}
                      </span>
                    ))}
                    {shelter.services.length > 3 && (
                      <span className="text-xs text-slate-400">+{shelter.services.length - 3} more</span>
                    )}
                  </div>
                )}

                <Button
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    getDirections(shelter.lat, shelter.lon);
                  }}
                  className="mt-3 bg-hearth hover:bg-amber-600 text-white btn-glow text-xs"
                  data-testid={`directions-button-${shelter.id}`}
                >
                  <Navigation className="w-3 h-3 mr-1" />
                  Get Directions
                </Button>
              </div>
            ))}

            {!loading && filteredShelters.length === 0 && (
              <div className="p-8 text-center">
                <p className="text-slate-400 font-manrope">No shelters match your criteria</p>
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-2 relative" data-testid="map-container">
          <MapContainer
            center={center}
            zoom={12}
            style={{ height: '100%', width: '100%' }}
            className="z-0"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <MapUpdater center={center} />
            
            {filteredShelters.map((shelter) => (
              <Marker
                key={shelter.id}
                position={[shelter.lat, shelter.lon]}
                icon={customIcon}
                eventHandlers={{
                  click: () => setSelectedShelter(shelter),
                }}
              >
                <Popup>
                  <div className="font-manrope">
                    <h4 className="font-bold mb-1">{shelter.name}</h4>
                    {shelter.address && (
                      <p className="text-sm mb-1">{shelter.address}</p>
                    )}
                    {shelter.phone && (
                      <p className="text-sm flex items-center mb-1">
                        <Phone className="w-3 h-3 mr-1" />
                        {shelter.phone}
                      </p>
                    )}
                    {shelter.website && (
                      <a
                        href={shelter.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-500 flex items-center hover:underline"
                      >
                        <Globe className="w-3 h-3 mr-1" />
                        Visit Website
                      </a>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      </div>
    </div>
  );
};

export default SearchResults;
