import requests
import sys
import json
from datetime import datetime

class WarmWishesAPITester:
    def __init__(self, base_url="https://warmhaven-finder.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            
            result = {
                "test_name": name,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "response_size": len(response.text) if response.text else 0
            }
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                # Try to parse JSON response
                try:
                    response_data = response.json()
                    result["response_data"] = response_data
                    if isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    elif isinstance(response_data, dict):
                        print(f"   Response: Dict with keys: {list(response_data.keys())}")
                except:
                    print(f"   Response: Non-JSON ({len(response.text)} chars)")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                result["error_response"] = response.text[:500]

            self.test_results.append(result)
            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {
                "test_name": name,
                "endpoint": endpoint,
                "method": method,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "success": False,
                "error": str(e)
            }
            self.test_results.append(result)
            return False, {}

    def test_root_endpoint(self):
        """Test API root endpoint"""
        success, response = self.run_test(
            "API Root",
            "GET",
            "api/",
            200
        )
        return success

    def test_organizations_endpoint(self):
        """Test organizations endpoint"""
        success, response = self.run_test(
            "Get Organizations",
            "GET",
            "api/organizations",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} organizations")
            if len(response) >= 4:
                print("   ✅ Expected 4 organizations found")
                # Check if organizations have required fields
                for i, org in enumerate(response[:2]):  # Check first 2
                    required_fields = ['name', 'description', 'website', 'donation_link']
                    missing_fields = [field for field in required_fields if field not in org]
                    if missing_fields:
                        print(f"   ⚠️  Organization {i+1} missing fields: {missing_fields}")
                    else:
                        print(f"   ✅ Organization {i+1} has all required fields")
            else:
                print(f"   ⚠️  Expected 4 organizations, got {len(response)}")
        
        return success

    def test_shelter_search_endpoint(self):
        """Test shelter search endpoint with real coordinates"""
        # Test with coordinates for New York City
        test_data = {
            "lat": 40.7128,
            "lon": -74.0060,
            "radius": 50000
        }
        
        success, response = self.run_test(
            "Shelter Search (NYC)",
            "POST",
            "api/shelters/search",
            200,
            data=test_data,
            timeout=45  # Longer timeout for Overpass API
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} shelters in NYC area")
            if len(response) > 0:
                # Check first shelter structure
                shelter = response[0]
                required_fields = ['id', 'name', 'lat', 'lon']
                missing_fields = [field for field in required_fields if field not in shelter]
                if missing_fields:
                    print(f"   ⚠️  Shelter missing required fields: {missing_fields}")
                else:
                    print(f"   ✅ Shelter has required fields")
                    print(f"   Sample shelter: {shelter.get('name', 'Unknown')}")
                    if shelter.get('services'):
                        print(f"   Services: {len(shelter['services'])} available")
                    if shelter.get('pet_friendly'):
                        print(f"   Pet friendly: {shelter['pet_friendly']}")
            else:
                print("   ⚠️  No shelters found (may be normal for test area)")
        
        return success

    def test_shelter_search_with_filters(self):
        """Test shelter search with filters"""
        test_data = {
            "lat": 40.7128,
            "lon": -74.0060,
            "radius": 50000,
            "pet_friendly": True,
            "services": ["meals", "healthcare"]
        }
        
        success, response = self.run_test(
            "Shelter Search with Filters",
            "POST",
            "api/shelters/search",
            200,
            data=test_data,
            timeout=45
        )
        
        if success:
            print(f"   Filtered results: {len(response)} shelters")
        
        return success

    def test_volunteer_form_submission(self):
        """Test volunteer form submission"""
        test_data = {
            "name": f"Test Volunteer {datetime.now().strftime('%H%M%S')}",
            "email": f"test{datetime.now().strftime('%H%M%S')}@example.com",
            "phone": "555-123-4567",
            "message": "I would like to volunteer to help with shelter operations."
        }
        
        success, response = self.run_test(
            "Volunteer Form Submission",
            "POST",
            "api/volunteer",
            200,
            data=test_data
        )
        
        if success and isinstance(response, dict):
            if 'id' in response and 'timestamp' in response:
                print(f"   ✅ Volunteer form created with ID: {response.get('id', 'Unknown')}")
            else:
                print(f"   ⚠️  Response missing expected fields")
        
        return success

    def test_volunteer_form_validation(self):
        """Test volunteer form validation with missing required fields"""
        test_data = {
            "phone": "555-123-4567",
            "message": "Missing name and email"
        }
        
        success, response = self.run_test(
            "Volunteer Form Validation (Missing Fields)",
            "POST",
            "api/volunteer",
            422,  # Expecting validation error
            data=test_data
        )
        
        return success

def main():
    print("🧪 Starting Warm Wishes API Testing...")
    print("=" * 50)
    
    tester = WarmWishesAPITester()
    
    # Run all tests
    tests = [
        tester.test_root_endpoint,
        tester.test_organizations_endpoint,
        tester.test_shelter_search_endpoint,
        tester.test_shelter_search_with_filters,
        tester.test_volunteer_form_submission,
        tester.test_volunteer_form_validation
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"📊 Test Summary:")
    print(f"   Tests run: {tester.tests_run}")
    print(f"   Tests passed: {tester.tests_passed}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'summary': {
                'tests_run': tester.tests_run,
                'tests_passed': tester.tests_passed,
                'success_rate': tester.tests_passed/tester.tests_run*100 if tester.tests_run > 0 else 0
            },
            'test_results': tester.test_results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())