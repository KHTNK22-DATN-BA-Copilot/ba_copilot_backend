"""
Integration test script for full stack (Backend + AI + Database).

This script tests the complete workflow by making actual HTTP requests
to the Docker services running on localhost.
"""

import requests
import time
import json
import sys

# Service URLs
BACKEND_URL = "http://localhost:8010"
AI_SERVICE_URL = "http://localhost:8000"

# Test data with unique timestamp to avoid conflicts
timestamp = int(time.time() * 1000)
TEST_USER = {
    "name": f"IntegrationTest User {timestamp}",
    "email": f"integration_test_{timestamp}@example.com",
    "passwordhash": "TestPassword123!"
}

TEST_PROJECT = {
    "name": f"Integration Test Project {timestamp}",
    "description": "Build an e-commerce platform with user authentication, product catalog, shopping cart, payment processing, and order management features."
}


def log(message, level="INFO"):
    """Print formatted log message."""
    print(f"[{level}] {message}")


def test_service_health():
    """Test that all services are healthy."""
    log("="*80)
    log("Testing Service Health")
    log("="*80)
    
    # Test backend health
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            log("✅ Backend service is healthy")
        else:
            log(f"❌ Backend service returned {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ Backend service is not reachable: {e}", "ERROR")
        return False
    
    # Test AI service health
    try:
        response = requests.get(f"{AI_SERVICE_URL}/v1/health/", timeout=5)
        if response.status_code == 200:
            log("✅ AI service is healthy")
        else:
            log(f"❌ AI service returned {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ AI service is not reachable: {e}", "ERROR")
        return False
    
    return True


def test_complete_workflow():
    """Test the complete workflow from registration to SRS generation."""
    log("\n" + "="*80)
    log("Starting Full Stack Integration Test: Complete Workflow")
    log("="*80 + "\n")
    
    # Step 1: Register user
    log("[STEP 1] User Registration")
    log(f"Registering user: {TEST_USER['email']}")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/register",
            json=TEST_USER,
            timeout=10
        )
        
        log(f"Registration Status Code: {response.status_code}")
        
        if response.status_code != 200:
            log(f"❌ Registration failed: {response.text}", "ERROR")
            return False
        
        user_data = response.json()
        log(f"✅ User registered successfully")
        
    except Exception as e:
        log(f"❌ Registration request failed: {e}", "ERROR")
        return False
    
    # Step 2: Login to get access token
    log("\n[STEP 2] User Login")
    log(f"Logging in user: {TEST_USER['email']}")
    
    login_data = {
        "email": TEST_USER["email"],
        "password": TEST_USER["passwordhash"]  # Using same password
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            data=login_data,  # Use data instead of json for form data
            timeout=10
        )
        
        log(f"Login Status Code: {response.status_code}")
        
        if response.status_code != 200:
            log(f"❌ Login failed: {response.text}", "ERROR")
            return False
        
        login_response = response.json()
        if "access_token" not in login_response:
            log(f"❌ No access token in login response", "ERROR")
            log(f"Response: {json.dumps(login_response, indent=2)}", "ERROR")
            return False
        
        access_token = login_response["access_token"]
        log(f"✅ User logged in successfully")
        
    except Exception as e:
        log(f"❌ Login request failed: {e}", "ERROR")
        return False
    
    # Step 3: Get user profile
    log("\n[STEP 3] Verify User Profile")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/user/me",
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            log(f"❌ Profile retrieval failed: {response.text}", "ERROR")
            return False
        
        profile_data = response.json()
        log(f"✅ User profile verified - Email: {profile_data['email']}")
        
    except Exception as e:
        log(f"❌ Profile request failed: {e}", "ERROR")
        return False
    
    # Step 3: Create project
    log("\n[STEP 4] Create Project")
    log(f"Creating project: {TEST_PROJECT['name']}")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/projects/",
            headers=headers,
            json=TEST_PROJECT,
            timeout=10
        )
        
        if response.status_code != 200:
            log(f"❌ Project creation failed: {response.text}", "ERROR")
            return False
        
        project_data = response.json()
        project_id = project_data.get("id")  # Use 'id' instead of 'project_id'
        log(f"✅ Project created successfully - Project ID: {project_id}")
        
    except Exception as e:
        log(f"❌ Project creation request failed: {e}", "ERROR")
        return False
    
    # Step 4: Generate SRS document
    log("\n[STEP 5] Generate SRS Document via AI Service")
    log("Sending request to backend which will call AI service...")
    
    srs_data = {
        "project_id": project_id,
        "project_name": TEST_PROJECT["name"],
        "description": TEST_PROJECT["description"]
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/srs/generate",
            headers=headers,
            data=srs_data,
            files=[],  # No files for this test
            timeout=180  # Allow 3 minutes for AI processing
        )
        
        log(f"SRS Generation Status Code: {response.status_code}")
        
        if response.status_code != 200:
            log(f"❌ SRS generation failed: {response.text}", "ERROR")
            try:
                error_detail = response.json()
                log(f"Error details: {json.dumps(error_detail, indent=2)}", "ERROR")
            except:
                pass
            return False
        
        srs_response = response.json()
        log(f"SRS Response Keys: {list(srs_response.keys())}")
        
        # Step 5: Verify AI service returned non-fallback response
        log("\n[STEP 6] Verify AI Service Response (Non-Fallback)")
        
        if "document" not in srs_response:
            log("❌ No document in SRS response", "ERROR")
            return False
        
        document = srs_response["document"]
        metadata = document.get("metadata", {})
        provider = metadata.get("provider", "unknown")
        
        log(f"AI Provider: {provider}")
        log(f"SRS Status: {srs_response.get('status', 'unknown')}")
        
        # CRITICAL: Ensure provider is NOT fallback
        if provider == "fallback":
            log("❌ CRITICAL: AI service returned FALLBACK response!", "ERROR")
            log("This indicates the AI service is not properly configured or API keys are missing.", "ERROR")
            log(f"Full metadata: {json.dumps(metadata, indent=2)}", "ERROR")
            return False
        
        log(f"✅ AI service returned REAL response - Provider: {provider}")
        
        # Verify document structure
        required_fields = ["title", "functional_requirements", "non_functional_requirements"]
        for field in required_fields:
            if field not in document:
                log(f"❌ Missing required field in document: {field}", "ERROR")
                return False
        
        functional_reqs = document.get("functional_requirements", [])
        log(f"Functional Requirements Count: {len(functional_reqs)}")
        
        if len(functional_reqs) == 0:
            log("❌ No functional requirements generated", "ERROR")
            return False
        
        log("✅ SRS document structure is valid")
        
    except requests.exceptions.Timeout:
        log("❌ SRS generation request timed out after 3 minutes", "ERROR")
        return False
    except Exception as e:
        log(f"❌ SRS generation request failed: {e}", "ERROR")
        return False
    
    # Success!
    log("\n" + "="*80)
    log("✅ FULL STACK INTEGRATION TEST PASSED!")
    log("="*80)
    log("Summary:")
    log(f"  - User Registration: ✅")
    log(f"  - User Login: ✅")
    log(f"  - User Profile: ✅")
    log(f"  - Project Creation: ✅")
    log(f"  - SRS Generation: ✅")
    log(f"  - AI Service (Non-Fallback): ✅ (Provider: {provider})")
    log(f"  - Document Structure: ✅")
    log("="*80 + "\n")
    log(f"\nThe SRS documents received:\n{srs_response}\n")
    
    return True


if __name__ == "__main__":
    log("BA Copilot - Full Stack Integration Test")
    log("Testing Backend, AI Service, and Database Integration\n")
    
    # Check if services are healthy first
    if not test_service_health():
        log("\n❌ Service health check failed. Please ensure all services are running.", "ERROR")
        log("Run: docker-compose up -d", "ERROR")
        sys.exit(1)
    
    # Run the complete workflow test
    success = test_complete_workflow()
    
    if success:
        log("\n🎉 All integration tests passed successfully!")
        sys.exit(0)
    else:
        log("\n❌ Integration tests failed. Please check the logs above for details.", "ERROR")
        sys.exit(1)
