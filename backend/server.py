from fastapi import FastAPI, APIRouter, HTTPException, Request, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import asyncio
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe setup
stripe_api_key = os.environ.get('STRIPE_API_KEY')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

class LockerSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class LockerStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"

# Database Models
class Locker(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int
    size: LockerSize
    status: LockerStatus = LockerStatus.AVAILABLE
    current_rental_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Rental(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    locker_id: str
    locker_number: int
    locker_size: LockerSize
    access_pin: str
    payment_session_id: Optional[str] = None
    payment_status: PaymentStatus = PaymentStatus.PENDING
    amount: float
    currency: str = "EUR"
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime
    is_expired: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    rental_id: str
    amount: float
    currency: str
    payment_status: PaymentStatus
    metadata: Dict
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request Models
class RentalRequest(BaseModel):
    locker_size: LockerSize

class UnlockRequest(BaseModel):
    locker_number: int
    access_pin: str

class CheckoutRequest(BaseModel):
    success_url: str
    cancel_url: str
    metadata: Optional[Dict] = {}

# Response Models
class LockerAvailability(BaseModel):
    size: LockerSize
    available_count: int
    price_per_24h: float

class RentalResponse(BaseModel):
    rental_id: str
    checkout_url: str
    session_id: str

class UnlockResponse(BaseModel):
    success: bool
    message: str
    locker_number: Optional[int] = None

# Pricing configuration
LOCKER_PRICES = {
    LockerSize.SMALL: 2.0,
    LockerSize.MEDIUM: 3.0,
    LockerSize.LARGE: 5.0
}

# Initialize lockers (run once)
async def initialize_lockers():
    """Initialize 24 lockers if they don't exist"""
    existing_count = await db.lockers.count_documents({})
    if existing_count > 0:
        return
    
    lockers = []
    # 8 small, 8 medium, 8 large
    for i in range(1, 25):  # 1-24
        if i <= 8:
            size = LockerSize.SMALL
        elif i <= 16:
            size = LockerSize.MEDIUM
        else:
            size = LockerSize.LARGE
        
        locker = Locker(number=i, size=size)
        lockers.append(locker.dict())
    
    await db.lockers.insert_many(lockers)
    print(f"Initialized {len(lockers)} lockers")

@app.on_event("startup")
async def startup_event():
    await initialize_lockers()
    # Start background task for checking expired rentals
    asyncio.create_task(check_expired_rentals())

async def check_expired_rentals():
    """Background task to check and handle expired rentals"""
    while True:
        try:
            current_time = datetime.now(timezone.utc)
            
            # Find expired rentals
            expired_rentals = await db.rentals.find({
                "end_time": {"$lt": current_time},
                "is_expired": False,
                "payment_status": PaymentStatus.SUCCESS
            }).to_list(None)
            
            for rental in expired_rentals:
                # Mark rental as expired
                await db.rentals.update_one(
                    {"id": rental["id"]},
                    {"$set": {"is_expired": True}}
                )
                
                # Free up the locker
                await db.lockers.update_one(
                    {"id": rental["locker_id"]},
                    {"$set": {
                        "status": LockerStatus.AVAILABLE,
                        "current_rental_id": None
                    }}
                )
                
                print(f"Expired rental {rental['id']} for locker {rental['locker_number']}")
        
        except Exception as e:
            print(f"Error checking expired rentals: {e}")
        
        await asyncio.sleep(60)  # Check every minute

def generate_pin():
    """Generate a 6-digit access PIN"""
    import random
    return f"{random.randint(100000, 999999)}"

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Luggage Storage System API"}

@api_router.get("/lockers/availability", response_model=List[LockerAvailability])
async def get_locker_availability():
    """Get availability and pricing for each locker size"""
    availability = []
    
    for size in LockerSize:
        available_count = await db.lockers.count_documents({
            "size": size,
            "status": LockerStatus.AVAILABLE
        })
        
        availability.append(LockerAvailability(
            size=size,
            available_count=available_count,
            price_per_24h=LOCKER_PRICES[size]
        ))
    
    return availability

@api_router.post("/rentals", response_model=RentalResponse)
async def create_rental(request: RentalRequest, http_request: Request):
    """Create a new rental and initiate payment"""
    
    # Check availability
    available_locker = await db.lockers.find_one({
        "size": request.locker_size,
        "status": LockerStatus.AVAILABLE
    })
    
    if not available_locker:
        raise HTTPException(
            status_code=400,
            detail=f"No {request.locker_size} lockers available"
        )
    
    # Create rental
    rental = Rental(
        locker_id=available_locker["id"],
        locker_number=available_locker["number"],
        locker_size=request.locker_size,
        access_pin=generate_pin(),
        amount=LOCKER_PRICES[request.locker_size],
        end_time=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    
    # Reserve the locker temporarily
    await db.lockers.update_one(
        {"id": available_locker["id"]},
        {"$set": {
            "status": LockerStatus.OCCUPIED,
            "current_rental_id": rental.id
        }}
    )
    
    # Insert rental
    await db.rentals.insert_one(rental.dict())
    
    # Create Stripe checkout session
    host_url = str(http_request.base_url).rstrip('/')
    success_url = f"{host_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/payment-cancelled"
    
    stripe_checkout = StripeCheckout(
        api_key=stripe_api_key,
        webhook_url=f"{host_url}/api/webhook/stripe"
    )
    
    checkout_request = CheckoutSessionRequest(
        amount=rental.amount,
        currency="EUR",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "rental_id": rental.id,
            "locker_number": str(rental.locker_number),
            "access_pin": rental.access_pin
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Update rental with session ID
    await db.rentals.update_one(
        {"id": rental.id},
        {"$set": {"payment_session_id": session.session_id}}
    )
    
    # Create payment transaction record
    transaction = PaymentTransaction(
        session_id=session.session_id,
        rental_id=rental.id,
        amount=rental.amount,
        currency=rental.currency,
        payment_status=PaymentStatus.PENDING,
        metadata=checkout_request.metadata
    )
    
    await db.payment_transactions.insert_one(transaction.dict())
    
    return RentalResponse(
        rental_id=rental.id,
        checkout_url=session.url,
        session_id=session.session_id
    )

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str):
    """Check payment status and update rental accordingly"""
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    
    try:
        status_response = await stripe_checkout.get_checkout_status(session_id)
        
        # Find the rental
        rental = await db.rentals.find_one({"payment_session_id": session_id})
        if not rental:
            raise HTTPException(status_code=404, detail="Rental not found")
        
        # Update payment transaction
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": PaymentStatus.SUCCESS if status_response.payment_status == "paid" else PaymentStatus.PENDING,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        # Update rental status if payment successful
        if status_response.payment_status == "paid":
            await db.rentals.update_one(
                {"id": rental["id"]},
                {"$set": {"payment_status": PaymentStatus.SUCCESS}}
            )
            
            return {
                "payment_status": "paid",
                "rental_id": rental["id"],
                "locker_number": rental["locker_number"],
                "access_pin": rental["access_pin"],
                "end_time": rental["end_time"].isoformat()
            }
        
        return {
            "payment_status": status_response.payment_status,
            "status": status_response.status
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/lockers/unlock", response_model=UnlockResponse)
async def unlock_locker(request: UnlockRequest):
    """Unlock locker with PIN code"""
    
    # Find active rental with matching PIN and locker number
    rental = await db.rentals.find_one({
        "locker_number": request.locker_number,
        "access_pin": request.access_pin,
        "payment_status": PaymentStatus.SUCCESS,
        "is_expired": False
    })
    
    if not rental:
        return UnlockResponse(
            success=False,
            message="Código PIN inválido ou cacifo não encontrado"
        )
    
    # Check if rental is expired
    current_time = datetime.now(timezone.utc)
    if current_time > rental["end_time"]:
        await db.rentals.update_one(
            {"id": rental["id"]},
            {"$set": {"is_expired": True}}
        )
        
        await db.lockers.update_one(
            {"number": request.locker_number},
            {"$set": {
                "status": LockerStatus.AVAILABLE,
                "current_rental_id": None
            }}
        )
        
        return UnlockResponse(
            success=False,
            message="Tempo de armazenamento expirado"
        )
    
    # Simulate hardware unlock (Raspberry Pi would trigger relay here)
    print(f"HARDWARE: Unlocking locker {request.locker_number}")
    
    return UnlockResponse(
        success=True,
        message="Cacifo desbloqueado com sucesso",
        locker_number=request.locker_number
    )

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """Handle Stripe webhooks"""
    
    body = await request.body()
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, stripe_signature)
        
        if webhook_response.event_type == "checkout.session.completed":
            # Update payment transaction
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {"$set": {
                    "payment_status": PaymentStatus.SUCCESS,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            # Update rental
            await db.rentals.update_one(
                {"payment_session_id": webhook_response.session_id},
                {"$set": {"payment_status": PaymentStatus.SUCCESS}}
            )
        
        return {"status": "success"}
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@api_router.get("/admin/lockers")
async def get_all_lockers():
    """Admin endpoint to view all lockers"""
    lockers = await db.lockers.find({}, {"_id": 0}).to_list(None)
    return lockers

@api_router.get("/admin/rentals")
async def get_all_rentals():
    """Admin endpoint to view all rentals"""
    rentals = await db.rentals.find({}, {"_id": 0}).to_list(None)
    return rentals

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()