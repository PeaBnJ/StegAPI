from fastapi import FastAPI, HTTPException, Depends, Security
import logging
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import secrets
from datetime import datetime, timedelta
import base64
from .steganography import hide_message, reveal_message
from fastapi.staticfiles import StaticFiles


# Load environment variables
load_dotenv()

SUPABASE_URL = "https://ermyzgicrdtazyjaejoa.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVybXl6Z2ljcmR0YXp5amFlam9hIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjI0MDExNywiZXhwIjoyMDUxODE2MTE3fQ.D3AsO_K49JW8PdunE2kMsnc6FuXrIEmoNXhudKGQ6ms"
SUPABASE_JWT_SECRET = "RGcO+lSknV1u4mZ2Wqq1bsQSb3BvBCbQUE2Tgj1CtAMVLVzA86iD6HB7E2eMo9rcGUbclqtHSfp6s4smQJslew=="

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.mount("/frontend", StaticFiles(directory="frontend/src", html=True), name="frontend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
header_scheme = APIKeyHeader(name="x-api-key", auto_error=True)

# Request models
class HideRequest(BaseModel):
    public: str
    private: str

class RevealRequest(BaseModel):
    public_with_hidden: str

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

# API Key Generation
def generate_unique_api_key():
    while True:
        new_api_key = secrets.token_hex(32)  # Generate a random API key
        # Check if the API key already exists in the database
        response = supabase.table("api_keys").select("api_key").eq("api_key", new_api_key).execute()
        if not response.data:  # If the API key does not exist, return it
            return new_api_key

# Validate API Key with expiration check
def validate_api_key(api_key: str = Security(header_scheme)):
    response = supabase.table("api_keys").select("user_id, expires_at").eq("api_key", api_key).execute()
    if not response.data:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    api_key_data = response.data[0]
    expires_at = api_key_data.get("expires_at")
    if expires_at and datetime.utcnow() > datetime.fromisoformat(expires_at):
        raise HTTPException(status_code=403, detail="API Key expired")

    return api_key_data["user_id"]

@app.post("/register")
async def register(req: RegisterRequest):
    try:
        # Register the user in Supabase
        response = supabase.auth.sign_up(
            {"email": req.email, "password": req.password}
        )
        return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

# Login endpoint (Token and API Key generation with expiration)
@app.post("/token")
async def login(req: LoginRequest):
    try:
        # Authenticate the user with Supabase
        response = supabase.auth.sign_in_with_password(
            {"email": req.email, "password": req.password}
        )

        session = response.session  # Assuming session is an attribute of the response

        if session:
            access_token = session.access_token  # Access token is directly under the session
            user_id = session.user.id  # User ID is also inside session.user

            # Generate a refresh token
            refresh_token = secrets.token_hex(32)
            refresh_token_expires_at = datetime.utcnow() + timedelta(days=30)  # Set expiration for 30 days

            # Insert refresh token into the database with expiration
            supabase.table("refresh_tokens").insert({
                "user_id": user_id,
                "refresh_token": refresh_token,
                "expires_at": refresh_token_expires_at.isoformat()
            }).execute()

            # Check if API key exists for the user
            api_key_response = supabase.table("api_keys").select("*").eq("user_id", user_id).execute()
            if not api_key_response.data:
                # Generate a new API key if one doesn't exist
                api_key = generate_unique_api_key()
                supabase.table("api_keys").insert({
                    "user_id": user_id,
                    "api_key": api_key
                }).execute()
            else:
                # Retrieve the existing API key
                api_key = api_key_response.data[0]["api_key"]

            # Return both tokens and API key
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": refresh_token_expires_at.isoformat(),
                "api_key": api_key
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")

# Logout endpoint
@app.post("/logout")
async def logout(req: RefreshRequest):
    try:
        # Log the incoming refresh token
        logging.info(f"Attempting to log out with refresh_token: {req.refresh_token}")

        # Check if the refresh token exists in the database
        response = supabase.table("refresh_tokens").select("*").eq("refresh_token", req.refresh_token).execute()

        # Log the response from Supabase
        logging.info(f"Supabase response: {response}")

        # If no data is found, raise an exception
        if not response.data:
            logging.warning("No matching refresh token found or already used.")
            raise HTTPException(status_code=400, detail="Invalid or already used refresh token")

        # If data is found, proceed to delete the refresh token
        delete_response = supabase.table("refresh_tokens").delete().eq("refresh_token", req.refresh_token).execute()

        # Log the response of the delete operation
        logging.info(f"Delete response: {delete_response}")

        # If deletion failed
        if not delete_response.data:
            raise HTTPException(status_code=500, detail="Failed to delete refresh token")

        return {"message": "Logged out successfully"}

    except Exception as e:
        # Log the exception for debugging
        logging.error(f"Error during logout: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")

# Hide message endpoint
@app.post("/hide/")
async def hide(req: HideRequest, user_id: str = Depends(validate_api_key)):
    # Perform steganography logic
    hidden_message = hide_message(req.public, req.private)
    print(hidden_message)
    return {"hidden_message": hidden_message, "user_id": user_id}

# Reveal message endpoint
@app.post("/reveal/")
async def reveal(req: RevealRequest, user_id: str = Depends(validate_api_key)):
    # Perform steganography logic
    revealed_message = reveal_message(req.public_with_hidden)
    return {"revealed_message": revealed_message, "user_id": user_id}

# Regenerate API key endpoint
@app.post("/regenerate-api-key/")
async def regenerate_api_key(user_id: str = Depends(validate_api_key)):
    try:
        # Generate a new unique API key
        new_api_key = generate_unique_api_key()
        expiration_date = datetime.utcnow() + timedelta(days=30)

        # Update the existing API key for the user
        response = supabase.table("api_keys").update({
            "api_key": new_api_key,
            "expires_at": expiration_date.isoformat()
        }).eq("user_id", user_id).execute()

        if not response.data:  # Check if data is empty
            raise Exception("Failed to update API key: No data returned")

        return {"api_key": new_api_key, "expires_at": expiration_date.isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate API key: {str(e)}")

@app.post("/refresh_token")
async def refresh_token(req: RefreshRequest):
    try:
        # Check if the refresh token exists in the database
        response = supabase.table("refresh_tokens").select("*").eq("refresh_token", req.refresh_token).execute()
        
        if not response.data:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Retrieve the refresh token's expiration date
        refresh_token_data = response.data[0]
        expires_at = refresh_token_data.get("expires_at")
        
        # Check if the refresh token has expired
        if datetime.utcnow() > datetime.fromisoformat(expires_at):
            raise HTTPException(status_code=401, detail="Refresh token expired")
        
        # Generate a new access token (this can be done using a JWT or another method you prefer)
        new_access_token = secrets.token_hex(32)  # Example: Replace with your own logic for generating access tokens
        
        return {"access_token": new_access_token}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh token: {str(e)}")
    
import httpx

# Load Furina encryption service key from environment variables
FURINA_SERVICE_URL = "https://furina-encryption-service.codebloop.my.id/api"
FURINA_SERVICE_KEY = "furina_60694ae83f6a4223860127a107792c93"

# Combined Request Models
class StegoEncryptRequest(BaseModel):
    public: str  # Public content (image or text where the encrypted message will be hidden)
    private: str  # Private message to encrypt and hide
    sensitivity: str  # Encryption sensitivity (e.g., "medium", "high")

class StegoDecryptRequest(BaseModel):
    key_id: str  # Key ID for decryption
    cipher_text: str  # Encrypted message (cipher_text)
    iv: str  # Initialization Vector for decryption

# Encryption Endpoint
@app.post("/stego/encrypt")
async def stego_encrypt(req: StegoEncryptRequest, user_id: str = Depends(validate_api_key)):
    try:
        # Step 1: Hide the private message inside the public content
        hidden_message = hide_message(req.public, req.private)  # This hides 'sup' inside 'helo'
        
        # Step 2: Encrypt the hidden message using Furina service
        encryption_payload = {"text": hidden_message, "sensitivity": req.sensitivity}
        async with httpx.AsyncClient() as client:
            encryption_response = await client.post(
                f"{FURINA_SERVICE_URL}/encrypt",
                headers={
                    "furina-encryption-service": FURINA_SERVICE_KEY,
                    "Content-Type": "application/json",
                },
                json=encryption_payload,
            )

        if encryption_response.status_code != 200:
            raise HTTPException(
                status_code=encryption_response.status_code,
                detail=f"Encryption failed: {encryption_response.text}",
            )

        encryption_data = encryption_response.json()

        # Step 3: Return the encrypted result, which includes the key_id, cipher_text, and iv
        return {
            "key_id": encryption_data["key_id"],
            "cipher_text": encryption_data["cipher_text"],
            "iv": encryption_data["iv"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stego-Encryption failed: {str(e)}")

# Decryption Endpoint
@app.post("/stego/decrypt")
async def stego_decrypt(req: StegoDecryptRequest, user_id: str = Depends(validate_api_key)):
    try:
        # Step 1: Decrypt the message using the Furina decryption service
        decryption_payload = {
            "key_id": req.key_id,
            "cipher_text": req.cipher_text,
            "iv": req.iv
        }

        async with httpx.AsyncClient() as client:
            decryption_response = await client.post(
                f"{FURINA_SERVICE_URL}/decrypt",
                headers={
                    "furina-encryption-service": FURINA_SERVICE_KEY,
                    "Content-Type": "application/json",
                },
                json=decryption_payload,
            )

        # If response is not successful, raise an error
        if decryption_response.status_code != 200:
            raise HTTPException(
                status_code=decryption_response.status_code,
                detail=f"Decryption failed: {decryption_response.text}",
            )

        # Step 2: After decryption, access the 'text' field instead of 'cipher_text'
        decrypted_data = decryption_response.json()

        if 'text' not in decrypted_data:
            raise HTTPException(status_code=400, detail="'text' not found in the response.")

        decrypted_cipher_text = decrypted_data['text']  # Use 'text' instead of 'cipher_text'

        # Step 3: Reveal the hidden message from the decrypted cipher_text (public_with_hidden)
        revealed_message = reveal_message(decrypted_cipher_text).strip()

        # Sanitize the revealed message
        revealed_message = revealed_message.replace("\ufeff", "").replace("\u200c", "").replace("\u2060", "")

        # Step 4: Return the decrypted result and the revealed message
        return {
            "encrypted_cipher_text": decrypted_cipher_text,  # This is the new public_with_hidden
            "revealed_public_with_hidden": revealed_message,   # The hidden message that was revealed
        }

    except Exception as e:
        # Log any exception details for easier debugging
        print(f"Error during decryption: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stego-Decryption failed: {str(e)}")