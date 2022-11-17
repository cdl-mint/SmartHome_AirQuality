from ast import And
import json
import os
from asyncio.log import logger
from datetime import datetime,timedelta
import uvicorn
import asyncio
from fastapi import Depends,FastAPI, HTTPException, status,Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from session import db_Session,settings
from databases import Database
from schema import Room,PeopleInRoom,Light, Light_Operation, Power_Plug, Power_Plug_Operation,Airqualityproperty
from fastAPI_models import User,UserInDB,Token,TokenData,Room_Object, Update_RoomObject, Lights_Object, Light_Operation_Object, Light_Operation_Return_Object, Update_LightObject, Time_Query_Object, Light_Operation_Storing_Object, Power_Plug_Object, Power_Plug_Update_Object, Power_Plug_Operation_Object, Power_Plug_Storing_Object,AirQuality_Properties_Object,AirQuality_Co2_Object,AirQuality_Temperature_Object,AirQuality_Humidity_Object,People_In_RoomObject,Light_Activation_Object
from typing import List,Union
from sqlalchemy import and_, text
from publisher import publish_message
from passlib.context import CryptContext
from jose import JWTError, jwt

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY ="ee46de360b7ab5ab35862b7285b51613a556da68764f8f1f2079988ccaed3681"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True,
    },
}
tags_metadata = [
    {
        "name": "Rooms",
        "description": "CRUD operations on room",
    },
    {
        "name": "Lights",
        "description": "Add lights in room, operate them (turn on/off) and change colors (use only hex color code)",
        "externalDocs": {
            "description": "sample hex color code",
            "url": "https://htmlcolorcodes.com/",
        },
    },
    {
        "name": "Ventilators",
        "description": "Attach ventilators to smart plug and operate them (turn on/off) based on indoor air quality",
        
    },
    {
        "name": "Doors",
        "description": "CRUD operations on doors- Not implemented",
    },
    {
        "name": "Windows",
        "description": "CRUD operations on windows- Not implemented",
    },
    {
        "name": "AirQuality",
        "description": "CRUD operations on air quality measurements (co2, temperature and humidity) in room",
        
    },
]
oauth2_scheme=OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title=settings.PROJECT_NAME,version=settings.PROJECT_VERSION, openapi_tags=tags_metadata)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def fake_hash_password(password: str):
    return "fakehashed" + password

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username] 
        
        return UserInDB(**user_dict)

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def fake_decode_token(token):
    user = get_user(fake_users_db, token)
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user:User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.post("/token",response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    print(form_data)
    user = authenticate_user(fake_users_db,form_data.username,form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

""" @app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user """
# Rooms

"""Creates a new room in the database and returns the room on success. Room_id needs to be unique"""
"""Example room object 
{
    "room_id": 1,
    "room_size": 50,
    "measurement_unit":"50 sq.m"
}"""
@app.post("/Rooms", tags=["Rooms"], response_model=Room_Object, status_code=status.HTTP_201_CREATED)
async def add_Room(addRoom: Room_Object,token:str = Depends(oauth2_scheme)):
    if(token):
     db_classes = Room(room_id=addRoom.room_id,room_size=addRoom.room_size, measurement_unit=addRoom.measurement_unit)
    else:
        return {"status:Not Authenticated"} 
    try:
        db_Session.add(db_classes)
        db_Session.flush()
        db_Session.commit()
    except Exception as ex:
        logger.error(f"{ex.__class__.__name__}: {ex}")
        db_Session.rollback()
    return addRoom

"""Returns all the rooms present in the database"""
@app.get("/Rooms", tags=["Rooms"],response_model=List[Room_Object], status_code=status.HTTP_200_OK)
async def get_AllRoom_Details(token:str = Depends(oauth2_scheme)):
    if(token):
        results = db_Session.query(Room).all()
        return results
    else:
        return {"status:Not Authenticated"}

""" Add number of people in room """
@app.post("/Rooms/{room_id}/PeopleInRoom",tags=["Rooms"], response_model=People_In_RoomObject, status_code=status.HTTP_201_CREATED)
async def add_People_Room(room_id: str,addPeopleRoom: People_In_RoomObject,token:str = Depends(oauth2_scheme)):
    if(token):
     db_classes = PeopleInRoom(room_id=room_id,people_count=addPeopleRoom.people_count)
    else:
        return {"status:Not Authenticated"} 
    try:
        db_Session.add(db_classes)
        db_Session.flush()
        db_Session.commit()
    except Exception as ex:
        logger.error(f"{ex.__class__.__name__}: {ex}")
        db_Session.rollback()
    return addPeopleRoom

"""Returns people count in room"""
@app.get("/Rooms/{room_id}/PeopleInRoom",tags=["Rooms"], response_model=People_In_RoomObject, status_code=status.HTTP_200_OK)
async def get_PeopleCount_Details(room_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
     peoplecount = db_Session.query(PeopleInRoom).filter(PeopleInRoom.room_id==room_id)
    else:
        return {"status:Not Authenticated"} 
    if not peoplecount.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'people in Room with the id {room_id} does not exist')
    return peoplecount

"""Returns a room with a certain room_id or an error if the room does not exist"""
@app.get("/Rooms/{room_id}",tags=["Rooms"], response_model= Room_Object, status_code=status.HTTP_200_OK)
async def get_Specific_Room(room_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
     specificRoomDetail = db_Session.query(Room).filter(Room.room_id == room_id)
    else:
        return {"status:Not Authenticated"}
    if not specificRoomDetail.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Room with the id {room_id} does not exist')
    return specificRoomDetail

"""Updates a room with a certain room_id or returns an error if the room does not exist"""
"""Example room update object 
   {
    "room_size": 55,
    "room_name": "Living room changed"
    }"""
@app.put("/Rooms/{room_id}",tags=["Rooms"], status_code=status.HTTP_200_OK)
async def update_RoomDetails(room_id: str, request: Update_RoomObject,token:str = Depends(oauth2_scheme)):
    if(token):
     updateRoomDetail = db_Session.query(Room).filter(Room.room_id == room_id)
    else:
       return {"status:Not Authenticated"} 
    if not updateRoomDetail.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Room with the id {room_id} is not available')
    updateRoomDetail.update(
        {'room_size': request.room_size, 'measurement_unit':request.measurement_unit})
    db_Session.commit()
    return {"code": "success", "message": "updated room"}

"""Deletes a room with a certain room_id or returns an error if the room does not exist"""
@app.delete("/Rooms/{room_id}",tags=["Rooms"], status_code=status.HTTP_200_OK)
async def delete_Room(room_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
     deleteRoom = db_Session.query(Room).filter(Room.room_id == room_id).one()
    else:
         return {"status:Not Authenticated"}
    if not deleteRoom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Room with the room id {room_id} is not found')
    db_Session.delete(deleteRoom)
    db_Session.commit()
    return {"code": "success", "message": f"deleted room with id {room_id}"}

# Lights
"""Creates a new light in a room in the database and returns the light on success. Light_id needs to be unique in the room (Light_id is unique per definition due to zigbee)"""
"""Example light object 
{
    "light_id": "0x804b50fffeb72fd9",
    "name": "Led Strip"
}"""
@app.post("/Rooms/{room_id}/Lights", tags=["Lights"], response_model=Lights_Object, status_code=status.HTTP_201_CREATED)
async def add_light(room_id: str, addLight: Lights_Object,token:str = Depends(oauth2_scheme)):
    if(token):
     addLight = Light(room_id=room_id, light_id=addLight.light_id, name=addLight.name)
    else:
        return {"status:Not Authenticated"} 
    try:
        db_Session.add(addLight)
        db_Session.flush()
        db_Session.commit()
        write_to_json("Lights", room_id, addLight.light_id)
    except Exception as ex:
        logger.error(f"{ex.__class__.__name__}: {ex}")
        db_Session.rollback()
    return addLight

"""Returns all the lights in a room"""
@app.get("/Rooms/{room_id}/Lights",tags=["Lights"], response_model=List[Lights_Object], status_code=status.HTTP_200_OK)
async def get_All_Lights(room_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
      getAllLights = db_Session.query(Light).filter(Light.room_id == room_id).all()
    else:
        return {"status:Not Authenticated"} 
    return getAllLights


"""Returns a specific light in a room or an error if the light does not exist in the room"""
@app.get("/Rooms/{room_id}/Lights/{light_id}/",tags=["Lights"], response_model=Lights_Object, status_code=status.HTTP_200_OK)
async def get_Specific_Light(room_id: str, light_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
     getSpecificLight = db_Session.query(Light).filter(Light.room_id == room_id, Light.light_id == light_id)
    else:
         return {"status:Not Authenticated"} 
    if not getSpecificLight.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Light with the id {light_id} is not available in room {room_id}')
    return getSpecificLight

"""Updates a specific light in a room and returns it or returns an error if the light does not exist in the room """
"""Example light object 
   {
    "name": "Led Strip changed"
    }"""
@app.put("/Rooms/{room_id}/Lights/{light_id}",tags=["Lights"], status_code=status.HTTP_200_OK)
async def update_light(room_id: str, light_id: str, request: Update_LightObject,token:str = Depends(oauth2_scheme)):
    if(token):
     updateLight = db_Session.query(Light).filter(Light.room_id == room_id, Light.light_id == light_id)
    else:
        return {"status:Not Authenticated"}  
    if not updateLight.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Light with the id {light_id} is not available in room {room_id}')
    updateLight.update({'name': request.name})
    db_Session.commit()
    return updateLight

"""Deletes a specific light in a room or returns an error if the light does not exist in the room"""
@app.delete("/Rooms/{room_id}/Lights/{light_id}",tags=["Lights"], status_code=status.HTTP_200_OK)
async def delete_light(room_id: str, light_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
     deleteLight = db_Session.query(Light).filter(Light.room_id == room_id, Light.light_id == light_id).one()
    else:
        return {"status:Not Authenticated"} 
    if not deleteLight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Light with the id {light_id} is not available in room {room_id}')
    db_Session.delete(deleteLight)
    db_Session.commit()
    delete_from_json(light_id)
    return {"code": "success", "message": f"deleted light with id {light_id} from room {room_id}"}

#  Lights Activation
"""Toggles a light in a room with a specific light_id"""
"""does not contain a body"""
@app.post("/Rooms/{room_id}/Lights/{light_id}/Activation",tags=["Lights"], status_code=status.HTTP_200_OK)
async def activate_Light(room_id: str, light_id: str,operation: Light_Activation_Object,token:str = Depends(oauth2_scheme)):
    if(token):
     data = {}
     #data["state"] = "TOGGLE"
     if operation.turnon == True:
        data["state"] = "ON"
     else:
        data["state"] = "OFF"
     topic = f"zigbee2mqtt/{light_id}/set"
     publish_message(topic, data)
     return {"code": "success", "message": "Device toggled"}
    else:
        return {"status:Not Authenticated"} 

""" Get the details of when the light is turned on/off """
@app.get("/Rooms/{room_id}/Lights/{light_id}/Activation",tags=["Lights"],response_model=List[Light_Operation_Return_Object], status_code=status.HTTP_200_OK)
async def activate_Light(room_id: str, light_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
     getLightDetails = db_Session.query(Light_Operation).filter(
        Light.room_id == room_id, Light.light_id == light_id)
    else:
        return {"status:Not Authenticated"}     
    if not getLightDetails.all():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Light with the id {light_id} is not available in room {room_id}')
    return getLightDetails

# Light set color
"""Changes the settings of a light via a Light Operation Objects."""
"""Example Light Operation Object 
   {
    "turnon": "ON",
    "brightness": 200,
    "color": {"hex":"#466bca"}
    }"""
@app.post("/Rooms/{room_id}/Lights/{light_id}/SetColor",tags=["Lights"], status_code=status.HTTP_200_OK)
async def complex_setting_light(room_id: str, light_id: str, operation: Light_Operation_Object,token:str = Depends(oauth2_scheme)):
    def isValidHexCode(str):
        if (str[0] != '#'):
            return False
        if (not(len(str) == 4 or len(str) == 7)):
            return False
        for i in range(1, len(str)):
            if (not((str[i] >= '0' and str[i] <= '9') or (str[i] >= 'a' and str[i] <= 'f') or (str[i] >= 'A' or str[i] <= 'F'))):
                return False
        return True
    data = {}
    color = {}
    if operation.turnon == True:
        data["state"] = "ON"
    else:
        data["state"] = "ON"

    if (isValidHexCode(operation.hex)):
        color["hex"] = operation.hex
    else:
        color["hex"]="#466bca"
    if(token):
     data["color"] = color
     data["brightness"] = operation.brightness
     topic = f"zigbee2mqtt/{light_id}/set"
     publish_message(topic, data)
    else:
         return {"status:Not Authenticated"} 
    return {"code": "success", "message": "Device Settings changed"}


# Ventilators
"""Creates a new power plug in a room in the database and returns the power plug on success. Plug_id needs to be unique in the room (Sensor_id is unique per definition due to zigbee)"""
"""Ventilators attached to smart power plug to turn or off"""
"""Example Power Plug object 
   {
    "plug_id": "0x804b50fffeb72fd9",
    "name": "Plug 1"
    }"""
@app.post("/Rooms/{room_id}/Ventilators",tags=["Ventilators"], response_model=Power_Plug_Object, status_code=status.HTTP_201_CREATED)
async def add_Power_Plug(room_id: str, addPowerPlug: Power_Plug_Object,token:str = Depends(oauth2_scheme)):
    if(token):
     addPowerPlug = Power_Plug(room_id=room_id, plug_id=addPowerPlug.plug_id, name=addPowerPlug.name)
    else:
       return {"status:Not Authenticated"} 
    try:
        db_Session.add(addPowerPlug)
        db_Session.flush()
        db_Session.commit()
        write_to_json("Power_Plugs", room_id, addPowerPlug.plug_id)
    except Exception as ex:
        logger.error(f"{ex.__class__.__name__}: {ex}")
        db_Session.rollback()
    return addPowerPlug

"""Returns all the power plug in a room"""
@app.get("/Rooms/{room_id}/Ventilators",tags=["Ventilators"], response_model=List[Power_Plug_Object], status_code=status.HTTP_200_OK)
async def get_All_Power_Plugs(room_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
     allPowerPlugs = db_Session.query(Power_Plug).filter(Power_Plug.room_id == room_id).all()
    else:
        return {"status:Not Authenticated"}
    return allPowerPlugs

"""Returns a specific power plug in a room or an error if the power plug does not exist in the room"""
@app.get("/Rooms/{room_id}/Ventilators/{plug_id}", tags=["Ventilators"],response_model=Power_Plug_Object, status_code=status.HTTP_200_OK)
async def get_Specific_Light(room_id: str, plug_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
     getSpecificPowerPlug = db_Session.query(Power_Plug).filter(
        Power_Plug.room_id == room_id, Power_Plug.plug_id == plug_id)
    else:
        return {"status:Not Authenticated"}   
    if not getSpecificPowerPlug.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Power Plug with the id {plug_id} is not available in room {room_id}')
    return getSpecificPowerPlug

"""Updates a specific power plug in a room and returns it or returns an error if the power plug does not exist in the room """
"""Example Power Plug update object 
   {
    "name": "Plug 1 changed"
    }"""
@app.put("/Rooms/{room_id}/Ventilators/{plug_id}",tags=["Ventilators"], response_model=Power_Plug_Object, status_code=status.HTTP_200_OK)
async def update_power_plug(room_id: str, plug_id: str, request: Power_Plug_Update_Object,token:str = Depends(oauth2_scheme)):
    if(token):
     updatePowerPlug = db_Session.query(Power_Plug).filter(
        Power_Plug.room_id == room_id, Power_Plug.plug_id == plug_id)
    else:
         return {"status:Not Authenticated"}     
    if not updatePowerPlug.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Motion Sensor with the id {plug_id} is not available in room {room_id}')
    updatePowerPlug.update({'name': request.name})
    db_Session.commit()
    return updatePowerPlug

"""Deletes a specific power plug  in a room or returns an error if the power plug does not exist in the room"""
@app.delete("/Rooms/{room_id}/Ventilators/{plug_id}",tags=["Ventilators"], status_code=status.HTTP_200_OK)
async def delete_power_plug(room_id: str, plug_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
     deletePowerPlug = db_Session.query(Power_Plug).filter(
        Power_Plug.room_id == room_id, Power_Plug.plug_id == plug_id).one()
    else:
        return {"status:Not Authenticated"}    
    if not deletePowerPlug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Light with the id {plug_id} is not available in room {room_id}')
    db_Session.delete(deletePowerPlug)
    db_Session.commit()
    delete_from_json(plug_id)
    return {"code": "success", "message": f"deleted light with id {plug_id} from room {room_id}"}

# Ventilators Operations

"""Post Operational Data for a power plug in a room"""
"""Example Operational Power Plug object 
    {
        "turnon": True
    }""" 
""" @app.post("/Rooms/{room_id}/Ventilators/{plug_id}/Operations", status_code = status.HTTP_200_OK)
async def post_operation_data_power_plugs(room_id: str, plug_id: str, body: Power_Plug_Storing_Object):
    new_operation = Power_Plug_Operation(room_id=room_id, plug_id=plug_id, time=datetime.now(), turnon = body.turnon)

    last_operation = db_Session.query(Power_Plug_Operation).filter(Power_Plug_Operation.room_id == room_id, Power_Plug_Operation.plug_id == plug_id).order_by(Power_Plug_Operation.time.desc()).first()

    #Lupus 12133 plugs are not completely compatible with zigbee2mqtt and tend to send multiple state events --> this ensures to only store one of the event states
    if last_operation == None or (last_operation != None and last_operation.turnon != new_operation.turnon):
        try:
            db_Session.add(new_operation)
            db_Session.flush()
            db_Session.commit()
        except Exception as ex:
            logger.error(f"{ex.__class__.__name__}: {ex}")
            db_Session.rollback()

    return new_operation """

"""Toggles a power plug(ventilator) in a room with a specific plug_id"""
"""does not contain a body"""
@app.post("/Rooms/{room_id}/Ventilators/{plug_id}/Activation",tags=["Ventilators"], status_code=status.HTTP_200_OK)
async def activate_Power_Plug(room_id: str, plug_id: str,body: Power_Plug_Storing_Object,token:str = Depends(oauth2_scheme)):
    if(token):
     new_operation = Power_Plug_Operation(room_id=room_id, plug_id=plug_id, time=datetime.now(), turnon = body.turnon)
    else:
        return {"status:Not Authenticated"}
    last_operation = db_Session.query(Power_Plug_Operation).filter(Power_Plug_Operation.room_id == room_id, Power_Plug_Operation.plug_id == plug_id).order_by(Power_Plug_Operation.time.desc()).first()

    #Lupus 12133 plugs are not completely compatible with zigbee2mqtt and tend to send multiple state events --> this ensures to only store one of the event states
    if last_operation == None or (last_operation != None and last_operation.turnon != new_operation.turnon):
        try:
            db_Session.add(new_operation)
            db_Session.flush()
            db_Session.commit()
        except Exception as ex:
            logger.error(f"{ex.__class__.__name__}: {ex}")
            db_Session.rollback()
    return new_operation

""" Get the details of when the Ventilator is turned on/off """
@app.get("/Rooms/{room_id}/Ventilators/{plug_id}/Activation",tags=["Ventilators"],response_model=List[Power_Plug_Operation_Object], status_code=status.HTTP_200_OK)
async def ventilator_Details(room_id: str, plug_id: str,token:str = Depends(oauth2_scheme)):
    if(token):
     getVentilatorDetails = db_Session.query(Power_Plug_Operation).filter(
        Power_Plug.room_id == room_id, Power_Plug.plug_id == plug_id)
    else:
        return {"status:Not Authenticated"}
    if not getVentilatorDetails.all():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Ventilator with the id {plug_id} is not available in room {room_id}')
    return getVentilatorDetails

#**Helper Methods**

"""Writes to devices.json after a new device is saved in the database"""
def write_to_json(device_type, device_room, device_key):
     with open("devices.json", 'r+') as f:
        devices = json.load(f)
        information = {}
        information["device_type"] = device_type
        information["device_room"] = device_room
        devices[device_key] = information
        f.seek(0)
        json.dump(devices, f, indent = 4)

"""Deletes a device from the device.json file once a device is deleted from the database"""
def delete_from_json(device_key):
    with open("devices.json", 'r+') as f:
        devices = json.load(f)
        f.truncate(0)
        del devices[device_key]
        f.seek(0)
        json.dump(devices, f, indent = 4)

#Air Quality APIs - airQualityinRoom

@app.post("/Room/AirQuality/",tags=["AirQuality"], response_model=AirQuality_Properties_Object, status_code = status.HTTP_201_CREATED)
async def add_AirQuality_Properties(addAirQuality:AirQuality_Properties_Object,token:str = Depends(oauth2_scheme)):
    if(token):
     db_AQP=Airqualityproperty(room_id=addAirQuality.room_id,device_id=addAirQuality.device_id,ventilator=addAirQuality.ventilator,co2=addAirQuality.co2,co2measurementunit=addAirQuality.co2measurementunit,temperature=addAirQuality.temperature,temperaturemeasurementunit=addAirQuality.temperaturemeasurementunit,humidity=addAirQuality.humidity,humiditymeasurementunit=addAirQuality.humiditymeasurementunit,time=addAirQuality.time)
    else:
      return {"status:Not Authenticated"}  
    try:
        db_Session.add(db_AQP)
        db_Session.flush()
        db_Session.commit()
    except Exception as ex:
        logger.error(f"{ex.__class__.__name__}: {ex}")
        db_Session.rollback()
    return addAirQuality

@app.get("/Room/{room_id}/AirQuality/",tags=["AirQuality"], response_model=AirQuality_Properties_Object, status_code = status.HTTP_200_OK)
async def get_AirQuality_Rooms(room_id:str,token:str = Depends(oauth2_scheme)):
    if(token):
     filteredAQPResults= db_Session.query(Airqualityproperty).filter(Airqualityproperty.room_id==room_id)
    else:
        return {"status:Not Authenticated"} 
    AQPresults=filteredAQPResults.order_by(Airqualityproperty.time.desc()).first()
    if not AQPresults:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f'No air quality measurements available for the room {room_id}')
    return AQPresults
    
@app.get("/Room/{room_id}/AirQuality/temperature/",tags=["AirQuality"], response_model=AirQuality_Temperature_Object, status_code = status.HTTP_200_OK)
async def get_AirQuality_Temperature(room_id:str,token:str = Depends(oauth2_scheme)):
    if(token):
     filteredAQTResults= db_Session.query(Airqualityproperty).filter(Airqualityproperty.room_id==room_id)
    else:
        return {"status:Not Authenticated"} 
    AQPTemperature=filteredAQTResults.order_by(Airqualityproperty.time.desc()).first()
    if not AQPTemperature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'No temperature data available for room id {room_id}')
    return AQPTemperature

@app.get("/Room/{room_id}/AirQuality/humidity/",tags=["AirQuality"], response_model=AirQuality_Humidity_Object, status_code = status.HTTP_200_OK)
async def get_AirQuality_Humidity(room_id:str,token:str = Depends(oauth2_scheme)):
    if(token):
     filteredAQHResults=db_Session.query(Airqualityproperty).filter(Airqualityproperty.room_id==room_id)
    else:
     return {"status:Not Authenticated"}
    AQPHumidity=filteredAQHResults.order_by(Airqualityproperty.time.desc()).first()
    if not AQPHumidity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'No humidity data available for room id {room_id}')
    return AQPHumidity

@app.get("/Room/{room_id}/AirQuality/co2/",tags=["AirQuality"], response_model=AirQuality_Co2_Object, status_code = status.HTTP_200_OK)
async def get_AirQuality_Co2(room_id:str,token:str = Depends(oauth2_scheme)):
    if(token):
     filteredAQCo2Results=db_Session.query(Airqualityproperty).filter(Airqualityproperty.room_id==room_id)
    else:
        return {"status:Not Authenticated"} 
    AQPCo2=filteredAQCo2Results.order_by(Airqualityproperty.time.desc()).first()
    if not AQPCo2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'No co2 data available for room id {room_id}')
    return AQPCo2    

# Doors
@app.post("/Rooms/{room_id}/Doors/", tags=["Doors"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def add_Door():
    addDoor=status.HTTP_501_NOT_IMPLEMENTED+f"-Not Implemented"
    return {addDoor}
@app.get("/Rooms/{room_id}/Doors/",tags=["Doors"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_Door():
    getDoor=status.HTTP_501_NOT_IMPLEMENTED
    return getDoor
@app.get("/Rooms/{room_id}/Doors/{door_id}",tags=["Doors"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_SpecificDoor():
    getSpecificDoor=status.HTTP_501_NOT_IMPLEMENTED
    return getSpecificDoor
@app.put("/Rooms/{room_id}/Doors/{door_id}",tags=["Doors"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def update_SpecificDoor():
    updateSpecificDoor=status.HTTP_501_NOT_IMPLEMENTED
    return updateSpecificDoor
@app.post("/Rooms/{room_id}/Doors/{door_id}/Open",tags=["Doors"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def open_Door():
    openSpecificDoor=status.HTTP_501_NOT_IMPLEMENTED
    return openSpecificDoor
@app.get("/Rooms/{room_id}/Doors/{door_id}/Open",tags=["Doors"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def getOpen_Door():
    detailDoorOperation=status.HTTP_501_NOT_IMPLEMENTED
    return detailDoorOperation

# Windows
@app.post("/Rooms/{room_id}/Windows/", tags=["Windows"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def add_Window():
    addWindow=status.HTTP_501_NOT_IMPLEMENTED
    return addWindow
@app.get("/Rooms/{room_id}/Windows/",tags=["Windows"],  status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_Window():
    getWindow=status.HTTP_501_NOT_IMPLEMENTED
    return getWindow
@app.get("/Rooms/{room_id}/Windows/{window_id}",tags=["Windows"],  status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_SpecificWindow():
    getSpecificWindow=status.HTTP_501_NOT_IMPLEMENTED
    return getSpecificWindow
@app.put("/Rooms/{room_id}/Windows/{window_id}",tags=["Windows"],  status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def update_SpecificWindow():
    UpdateSpecificWindow=status.HTTP_501_NOT_IMPLEMENTED
    return UpdateSpecificWindow
@app.post("/Rooms/{room_id}/Windows/{window_id}/Open", tags=["Windows"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def open_Window():
    openSpecificWindow=status.HTTP_501_NOT_IMPLEMENTED
    return openSpecificWindow
@app.get("/Rooms/{room_id}/Windows/{window_id}/Open",tags=["Windows"],  status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def getOpen_Window():
    detailWindowOperation=status.HTTP_501_NOT_IMPLEMENTED
    return detailWindowOperation