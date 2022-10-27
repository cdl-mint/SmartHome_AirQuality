from sqlite3 import Timestamp
from xmlrpc.client import DateTime
from pydantic import BaseModel
from datetime import datetime

#Smart_Room
class Room_Object(BaseModel):
    room_id: str
    people_count:int
    room_size:int
    measurement_unit:str

    class Config:
        orm_mode = True

class Update_RoomObject(BaseModel):
    room_size:int
    measurement_unit:str
  
    class Config:
        orm_mode = True

class Lights_Object(BaseModel):
    light_id: str
    name: str
    

    class Config:
        orm_mode = True

class Update_LightObject(BaseModel):
    name: str

    class Config:
        orm_mode = True


class Light_Operation_Object(BaseModel):
    turnon:bool
    brightness: int
    hex: str

    
    class Config:
        orm_mode = True        

class Light_Operation_Storing_Object(BaseModel):
    turnon:bool
    brightness: int
    color_x: float
    color_y: float

    class Config:
        orm_mode = True  

class Light_Operation_Return_Object(BaseModel):
    turnon:bool
    brightness: int
    color_x: float
    color_y: float
    time: Timestamp
    
    class Config:
        orm_mode = True



class Time_Query_Object(BaseModel):
    interval: int
    timespan_from: int
    timespan_to: int
    


class Motion_Sensor_Object(BaseModel):
    sensor_id: str
    name: str

    class Config:
        orm_mode = True        

class Motion_Sensor_Update_Object(BaseModel):
    name: str

    class Config:
        orm_mode = True


class Motion_Sensor_Operation_Object(BaseModel):
    detection: bool
    time: Timestamp

    class Config:
        orm_mode = True

class Motion_Sensor_Storing_Object(BaseModel):
    detection:bool

    class Config:
        orm_mode = True


class Power_Plug_Object(BaseModel):
    plug_id: str
    name: str

    class Config:
        orm_mode = True

class Power_Plug_Operation_Object(BaseModel):
    turnon: bool
    time: Timestamp
    class Config:
        orm_mode = True

class Power_Plug_Update_Object(BaseModel):
    name: str

    class Config:
        orm_mode = True

class Power_Plug_Storing_Object(BaseModel):
    turnon:bool

    class Config:
        orm_mode = True

#Air Quality
 
class AirQuality_Properties_Object(BaseModel):
    room_id: str
    device_id:str
    ventilator:str
    co2:float
    co2measurementunit:str
    temperature:float
    temperaturemeasurementunit:str
    humidity:float
    humiditymeasurementunit:str
    time:Timestamp
    
    class Config:
        orm_mode = True

class AirQuality_Temperature_Object(BaseModel):
    room_id: str
    ventilator:str
    temperature:int
    temperaturemeasurementunit:str
    time:Timestamp
    
    class Config:
        orm_mode = True

class AirQuality_Humidity_Object(BaseModel):
    room_id: str
    ventilator:str
    humidity:int
    humiditymeasurementunit:str
    time:Timestamp
    
    class Config:
        orm_mode = True     

class AirQuality_Co2_Object(BaseModel):
    room_id: str
    ventilator:str
    co2:int
    co2measurementunit:str
    time:Timestamp
    
    class Config:
        orm_mode = True             


