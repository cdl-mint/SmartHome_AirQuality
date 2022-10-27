from ast import And
import json
import os
from asyncio.log import logger
from datetime import datetime
import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from session import db_Session,settings
from databases import Database
from schema import Room, Light, Light_Operation, Power_Plug, Power_Plug_Operation,Airqualityproperty
from fastAPI_models import Room_Object, Update_RoomObject, Lights_Object, Light_Operation_Object, Light_Operation_Return_Object, Update_LightObject, Time_Query_Object, Light_Operation_Storing_Object, Power_Plug_Object, Power_Plug_Update_Object, Power_Plug_Operation_Object, Power_Plug_Storing_Object,AirQuality_Properties_Object,AirQuality_Co2_Object,AirQuality_Temperature_Object,AirQuality_Humidity_Object
from typing import List
from sqlalchemy import and_, text
from publisher import publish_message


app = FastAPI(title=settings.PROJECT_NAME,
rootpath="/smartRoom_AirQuality")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Rooms

"""Creates a new room in the database and returns the room on success. Room_id needs to be unique"""
"""Example room object 
   {
    "room_id": 1,
    "room_size": 50,
    "people_count":2,
    "measurement_unit":"50 sq.m"
    }"""
@app.post("/Rooms", response_model=Room_Object, status_code=status.HTTP_201_CREATED)
async def add_Room(addRoom: Room_Object):
    db_classes = Room(room_id=addRoom.room_id, people_count=addRoom.people_count,
                      room_size=addRoom.room_size, measurement_unit=addRoom.measurement_unit)
    try:
        db_Session.add(db_classes)
        db_Session.flush()
        db_Session.commit()
    except Exception as ex:
        logger.error(f"{ex.__class__.__name__}: {ex}")
        db_Session.rollback()

    return addRoom

"""Returns all the rooms present in the database"""
@app.get("/Rooms", response_model=List[Room_Object], status_code=status.HTTP_200_OK)
async def get_AllRoom_Details():
    results = db_Session.query(Room).all()
    return results

"""Returns a room with a certain room_id or an error if the room does not exist"""
@app.get("/Rooms/{room_id}", response_model= Room_Object, status_code=status.HTTP_200_OK)
async def get_Specific_Room(room_id: str):
    specificRoomDetail = db_Session.query(
        Room).filter(Room.room_id == room_id)

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
@app.put("/Rooms/{room_id}", status_code=status.HTTP_200_OK)
async def update_RoomDetails(room_id: str, request: Update_RoomObject):
    updateRoomDetail = db_Session.query(Room).filter(Room.room_id == room_id)
    if not updateRoomDetail.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Room with the id {room_id} is not available')
    updateRoomDetail.update(
        {'room_size': request.room_size, 'measurement_unit':request.measurement_unit})
    db_Session.commit()
    return {"code": "success", "message": "updated room"}

"""Deletes a room with a certain room_id or returns an error if the room does not exist"""
@app.delete("/Rooms/{room_id}", status_code=status.HTTP_200_OK)
async def delete_Room(room_id: str):
    deleteRoom = db_Session.query(Room).filter(Room.room_id == room_id).one()
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
@app.post("/Rooms/{room_id}/Lights", response_model=Lights_Object, status_code=status.HTTP_201_CREATED)
async def add_light(room_id: str, addLight: Lights_Object):
    addLight = Light(
        room_id=room_id, light_id=addLight.light_id, name=addLight.name)
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
@app.get("/Rooms/{room_id}/Lights", response_model=List[Lights_Object], status_code=status.HTTP_200_OK)
async def get_All_Lights(room_id: str):
    getAllLights = db_Session.query(Light).filter(
        Light.room_id == room_id).all()
    return getAllLights


"""Returns a specific light in a room or an error if the light does not exist in the room"""
@app.get("/Rooms/{room_id}/Lights/{light_id}/", response_model=Lights_Object, status_code=status.HTTP_200_OK)
async def get_Specific_Light(room_id: str, light_id: str):
    getSpecificLight = db_Session.query(Light).filter(
        Light.room_id == room_id, Light.light_id == light_id)
    if not getSpecificLight.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Light with the id {light_id} is not available in room {room_id}')
    return getSpecificLight

"""Updates a specific light in a room and returns it or returns an error if the light does not exist in the room """
"""Example light object 
   {
    "name": "Led Strip changed"
    }"""
@app.put("/Rooms/{room_id}/Lights/{light_id}", status_code=status.HTTP_200_OK)
async def update_light(room_id: str, light_id: str, request: Update_LightObject):
    updateLight = db_Session.query(Light).filter(
        Light.room_id == room_id, Light.light_id == light_id)
    if not updateLight.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Light with the id {light_id} is not available in room {room_id}')
    updateLight.update({'name': request.name})
    db_Session.commit()
    return updateLight

"""Deletes a specific light in a room or returns an error if the light does not exist in the room"""
@app.delete("/Rooms/{room_id}/Lights/{light_id}", status_code=status.HTTP_200_OK)
async def delete_light(room_id: str, light_id: str):
    deleteLight = db_Session.query(Light).filter(
        Light.room_id == room_id, Light.light_id == light_id).one()
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
@app.post("/Rooms/{room_id}/Lights/{light_id}/Activation", status_code=status.HTTP_200_OK)
async def activate_Light(room_id: str, light_id: str):

    data = {}
    data["state"] = "TOGGLE"
    topic = f"zigbee2mqtt/{light_id}/set"

    publish_message(topic, data)

    return {"code": "success", "message": "Device toggled"}

# Light set color
"""Changes the settings of a light via a Light Operation Objects."""
"""Example Light Operation Object 
   {
    "turnon": "ON",
    "brightness": 200,
    "color": {"hex":"#466bca"}
    }"""
@app.post("/Rooms/{room_id}/Lights/{light_id}/SetColor", status_code=status.HTTP_200_OK)
async def complex_setting_light(room_id: str, light_id: str, operation: Light_Operation_Object):
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
        data["state"] = "OFF"

    if (isValidHexCode(operation.hex)):
        color["hex"] = operation.hex
    else:
        color["hex"]="#466bca"
        
    data["color"] = color
    data["brightness"] = operation.brightness

    topic = f"zigbee2mqtt/{light_id}/set"

    publish_message(topic, data)

    return {"code": "success", "message": "Device Settings changed"}


# Ventilators
"""Creates a new power plug in a room in the database and returns the power plug on success. Plug_id needs to be unique in the room (Sensor_id is unique per definition due to zigbee)"""
"""Ventilators attached to smart power plug to turn or off"""
"""Example Power Plug object 
   {
    "plug_id": "0x804b50fffeb72fd9",
    "name": "Plug 1"
    }"""
@app.post("/Rooms/{room_id}/Ventilators", response_model=Power_Plug_Object, status_code=status.HTTP_201_CREATED)
async def add_Power_Plug(room_id: str, addPowerPlug: Power_Plug_Object):
    addPowerPlug = Power_Plug(
        room_id=room_id, plug_id=addPowerPlug.plug_id, name=addPowerPlug.name)
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
@app.get("/Rooms/{room_id}/Ventilators", response_model=List[Power_Plug_Object], status_code=status.HTTP_200_OK)
async def get_All_Power_Plugs(room_id: str):
    allPowerPlugs = db_Session.query(Power_Plug).filter(
        Power_Plug.room_id == room_id).all()
    return allPowerPlugs

"""Returns a specific power plug in a room or an error if the power plug does not exist in the room"""
@app.get("/Rooms/{room_id}/Ventilators/{plug_id}", response_model=Power_Plug_Object, status_code=status.HTTP_200_OK)
async def get_Specific_Light(room_id: str, plug_id: str):
    getSpecificPowerPlug = db_Session.query(Power_Plug).filter(
        Power_Plug.room_id == room_id, Power_Plug.plug_id == plug_id)
    if not getSpecificPowerPlug.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Power Plug with the id {plug_id} is not available in room {room_id}')
    return getSpecificPowerPlug

"""Updates a specific power plug in a room and returns it or returns an error if the power plug does not exist in the room """
"""Example Power Plug update object 
   {
    "name": "Plug 1 changed"
    }"""
@app.put("/Rooms/{room_id}/Ventilators/{plug_id}", response_model=Power_Plug_Object, status_code=status.HTTP_200_OK)
async def update_power_plug(room_id: str, plug_id: str, request: Power_Plug_Update_Object):
    updatePowerPlug = db_Session.query(Power_Plug).filter(
        Power_Plug.room_id == room_id, Power_Plug.plug_id == plug_id)
    if not updatePowerPlug.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Motion Sensor with the id {plug_id} is not available in room {room_id}')
    updatePowerPlug.update({'name': request.name})
    db_Session.commit()
    return updatePowerPlug

"""Deletes a specific power plug  in a room or returns an error if the power plug does not exist in the room"""
@app.delete("/Rooms/{room_id}/Ventilators/{plug_id}", status_code=status.HTTP_200_OK)
async def delete_power_plug(room_id: str, plug_id: str):
    deletePowerPlug = db_Session.query(Power_Plug).filter(
        Power_Plug.room_id == room_id, Power_Plug.plug_id == plug_id).one()
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
@app.post("/Rooms/{room_id}/Ventilators/{plug_id}/Operations", status_code = status.HTTP_200_OK)
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

    return new_operation

"""Toggles a power plug(ventilator) in a room with a specific plug_id"""
"""does not contain a body"""
@app.post("/Rooms/{room_id}/Ventilators/{plug_id}/Activation", status_code=status.HTTP_200_OK)
async def activate_Power_Plug(room_id: str, plug_id: str):

    data = {}
    data["state"] = "TOGGLE"
    topic = f"zigbee2mqtt/{plug_id}/set"

    publish_message(topic, data)

    return {"code": "success", "message": "Device toggled"}


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

#Air Quality APIs

# airQualityinRoom

@app.post("/Room/AirQuality/", response_model=AirQuality_Properties_Object, status_code = status.HTTP_201_CREATED)
async def add_AirQuality_Properties(addAirQuality:AirQuality_Properties_Object):
    db_AQP=Airqualityproperty(room_id=addAirQuality.room_id,device_id=addAirQuality.device_id,ventilator=addAirQuality.ventilator,co2=addAirQuality.co2,co2measurementunit=addAirQuality.co2measurementunit,temperature=addAirQuality.temperature,temperaturemeasurementunit=addAirQuality.temperaturemeasurementunit,humidity=addAirQuality.humidity,humiditymeasurementunit=addAirQuality.humiditymeasurementunit,time=addAirQuality.time)
    try:
        db_Session.add(db_AQP)
        db_Session.flush()
        db_Session.commit()
    except Exception as ex:
        logger.error(f"{ex.__class__.__name__}: {ex}")
        db_Session.rollback()
        
    return addAirQuality

@app.get("/Room/{room_id}/AirQuality/", response_model=AirQuality_Properties_Object, status_code = status.HTTP_200_OK)
async def get_AirQuality_Rooms(room_id:str):
    filteredAQPresults= db_Session.query(Airqualityproperty).filter(Airqualityproperty.room_id==room_id)
    AQPresults=filteredAQPresults.order_by(Airqualityproperty.time.desc()).first()
    return AQPresults
    
@app.get("/Room/{room_id}/AirQuality/temperature/", response_model=List[AirQuality_Temperature_Object], status_code = status.HTTP_200_OK)
async def get_AirQuality_Temperature(room_id:str):
    AQPTemperature=db_Session.query(Airqualityproperty.room_id,Airqualityproperty.temperature,Airqualityproperty.temperaturemeasurementunit,Airqualityproperty.ventilator,Airqualityproperty.time).filter(Airqualityproperty.room_id==room_id)
    if not AQPTemperature.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'No temperature data available for room id {room_id}')
    return AQPTemperature

@app.get("/Room/{room_id}/AirQuality/humidity/", response_model=List[AirQuality_Humidity_Object], status_code = status.HTTP_200_OK)
async def get_AirQuality_Humidity(room_id:str):
    AQPHumidity=db_Session.query(Airqualityproperty.room_id,Airqualityproperty.humidity,Airqualityproperty.humiditymeasurementunit,Airqualityproperty.ventilator,Airqualityproperty.time).filter(Airqualityproperty.room_id==room_id)
    if not AQPHumidity.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'No humidity data available for room id {room_id}')
    return AQPHumidity

@app.get("/Room/{room_id}/AirQuality/co2/", response_model=List[AirQuality_Co2_Object], status_code = status.HTTP_200_OK)
async def get_AirQuality_Co2(room_id:str):
    AQPCo2=db_Session.query(Airqualityproperty.room_id,Airqualityproperty.co2,Airqualityproperty.co2measurementunit,Airqualityproperty.ventilator,Airqualityproperty.time).filter(Airqualityproperty.room_id==room_id)
    if not AQPCo2.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'No co2 data available for room id {room_id}')
    return AQPCo2    