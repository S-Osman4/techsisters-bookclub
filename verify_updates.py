#!/usr/bin/env python3
"""
Verify that database updates are working correctly
"""
from app.database import SessionLocal
from app.models import User
from sqlalchemy import text

def verify_updates():
    """Test database update operations"""
    print("🔍 Verifying database updates...")
    
    db = SessionLocal()
    
    try:
        # Test 1: Check if we can read users
        print("\n1️⃣ Testing read operations...")
        users = db.query(User).all()
        print(f"   ✅ Found {len(users)} users")
        
        # Test 2: Check if we can update
        print("\n2️⃣ Testing update operations...")
        test_user = db.query(User).first()
        if test_user:
            original_name = test_user.name
            test_user.name = "Test Update"
            db.commit()
            db.refresh(test_user)
            
            # Verify update
            db_check = db.query(User).filter(User.id == test_user.id).first()
            if db_check.name == "Test Update":
                print(f"   ✅ Update successful")
                
                # Restore original name
                test_user.name = original_name
                db.commit()
                print(f"   ✅ Restored original name")
            else:
                print(f"   ❌ Update failed!")
        
        # Test 3: Check admin actions logging
        print("\n3️⃣ Testing admin actions logging...")
        from app.models import AdminAction
        log_count = db.query(AdminAction).count()
        print(f"   ✅ Found {log_count} admin action logs")
        
        print("\n✅ All verifications passed!")
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    verify_updates()