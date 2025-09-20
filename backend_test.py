import requests
import sys
import json
from datetime import datetime
import time

class LuggageStorageAPITester:
    def __init__(self, base_url="https://lockit.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'PUT':
                response = self.session.put(url, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Exception: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )

    def test_locker_availability(self):
        """Test getting locker availability"""
        success, data = self.run_test(
            "Locker Availability",
            "GET", 
            "lockers/availability",
            200
        )
        
        if success and isinstance(data, list):
            print(f"   Found {len(data)} locker sizes")
            for locker in data:
                print(f"   - {locker.get('size', 'unknown')}: {locker.get('available_count', 0)} available at €{locker.get('price_per_24h', 0)}")
        
        return success, data

    def test_create_rental(self, locker_size="small"):
        """Test creating a rental"""
        success, data = self.run_test(
            f"Create Rental ({locker_size})",
            "POST",
            "rentals",
            200,
            data={"locker_size": locker_size}
        )
        
        if success:
            rental_id = data.get('rental_id')
            session_id = data.get('session_id')
            checkout_url = data.get('checkout_url')
            print(f"   Rental ID: {rental_id}")
            print(f"   Session ID: {session_id}")
            print(f"   Checkout URL: {checkout_url[:50]}..." if checkout_url else "No checkout URL")
            return success, data
        
        return success, data

    def test_payment_status(self, session_id):
        """Test checking payment status"""
        return self.run_test(
            "Payment Status Check",
            "GET",
            f"payments/status/{session_id}",
            200
        )

    def test_unlock_locker_invalid(self):
        """Test unlocking with invalid credentials"""
        return self.run_test(
            "Unlock Locker (Invalid PIN)",
            "POST",
            "lockers/unlock",
            200,
            data={
                "locker_number": 1,
                "access_pin": "000000"
            }
        )

    def test_admin_endpoints(self):
        """Test admin endpoints"""
        print("\n📊 Testing Admin Endpoints...")
        
        # Test get all lockers
        success1, lockers = self.run_test(
            "Admin - Get All Lockers",
            "GET",
            "admin/lockers",
            200
        )
        
        if success1 and isinstance(lockers, list):
            print(f"   Total lockers in system: {len(lockers)}")
            sizes = {}
            statuses = {}
            for locker in lockers:
                size = locker.get('size', 'unknown')
                status = locker.get('status', 'unknown')
                sizes[size] = sizes.get(size, 0) + 1
                statuses[status] = statuses.get(status, 0) + 1
            
            print(f"   Sizes: {sizes}")
            print(f"   Statuses: {statuses}")
        
        # Test get all rentals
        success2, rentals = self.run_test(
            "Admin - Get All Rentals",
            "GET",
            "admin/rentals",
            200
        )
        
        if success2 and isinstance(rentals, list):
            print(f"   Total rentals in system: {len(rentals)}")
            if rentals:
                recent_rental = rentals[-1]
                print(f"   Most recent rental: Locker {recent_rental.get('locker_number')} - Status: {recent_rental.get('payment_status')}")
        
        return success1 and success2

    def test_invalid_endpoints(self):
        """Test invalid endpoints and error handling"""
        print("\n🚫 Testing Error Handling...")
        
        # Test invalid locker size
        success1, _ = self.run_test(
            "Invalid Locker Size",
            "POST",
            "rentals",
            422,  # Validation error
            data={"locker_size": "invalid_size"}
        )
        
        # Test invalid session ID
        success2, _ = self.run_test(
            "Invalid Session ID",
            "GET",
            "payments/status/invalid_session_id",
            400  # Bad request
        )
        
        # Test unlock with missing data
        success3, _ = self.run_test(
            "Unlock Missing Data",
            "POST",
            "lockers/unlock",
            422,  # Validation error
            data={}
        )
        
        return success1 or success2 or success3  # At least one should handle errors correctly

def main():
    print("🏪 Starting Luggage Storage System API Tests")
    print("=" * 60)
    
    tester = LuggageStorageAPITester()
    
    # Test basic connectivity
    print("\n🔌 Testing Basic Connectivity...")
    if not tester.test_root_endpoint()[0]:
        print("❌ Cannot connect to API. Stopping tests.")
        return 1
    
    # Test core functionality
    print("\n🏪 Testing Core Functionality...")
    
    # Test locker availability
    availability_success, availability_data = tester.test_locker_availability()
    if not availability_success:
        print("❌ Locker availability test failed")
        return 1
    
    # Test rental creation
    rental_success, rental_data = tester.test_create_rental("small")
    session_id = None
    if rental_success:
        session_id = rental_data.get('session_id')
    
    # Test payment status (will be pending since no actual payment)
    if session_id:
        tester.test_payment_status(session_id)
    
    # Test unlock with invalid credentials
    tester.test_unlock_locker_invalid()
    
    # Test admin endpoints
    tester.test_admin_endpoints()
    
    # Test error handling
    tester.test_invalid_endpoints()
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())