import os  
import random  
import json  
from datetime import datetime  
from typing import List, Dict, Union  
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey  
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker, relationship  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
from scipy import spatial  
from pathlib import Path  
from .tools import Tool  

Base = declarative_base()  

class Customer(Base):  
    __tablename__ = 'customers'  
    id = Column(String, primary_key=True)  
    name = Column(String)  
    reservations = relationship('Reservation', backref='customer')  
  
class Reservation(Base):  
    __tablename__ = 'reservations'  
    id = Column(Integer, primary_key=True, autoincrement=True)  
    customer_id = Column(String, ForeignKey('customers.id'))  
    hotel_id = Column(String)  
    room_type = Column(String)  
    check_in_date = Column(DateTime)  
    check_out_date = Column(DateTime)  
    status = Column(String)  
  
class HotelAgentTool(Tool):  
    def __init__(self):  
        super().__init__()
        emb_map_file_path=os.getenv("HOTEL_POLICY_FILE")  
        with open(emb_map_file_path) as file:  
            self.chunks_emb = json.load(file)  
  
          
  
        # SQLAlchemy setup  
        engine = create_engine(f'sqlite:///{os.getenv("HOTEL_DB_FILE")}')  
        Base.metadata.create_all(engine)  
        Session = sessionmaker(bind=engine)  
        self.session = Session()  
  
        # Azure OpenAI setup  
        self.openai_emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")  
        self.openai_chat_engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
        self.openai_client = AzureOpenAI(  
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")  
        )  
  
    def search_hotel_knowledgebase(self, search_query: str) -> str:  
        print("search_hotel_knowledgebase")  
        return self.search_knowledge_base(search_query, topk=3)  
  
    def query_rooms(self, hotel_id: str, check_in_date: str, check_out_date: str) -> str:  
        print("query_rooms")  
        room_types = ["Standard", "Deluxe", "Suite"]  
        rooms = "\n".join(  
            f"Room type: {room_type}, Hotel ID: {hotel_id}, Check-in: {check_in_date}, Check-out: {check_out_date}, Status: Available"  
            for room_type in room_types  
        )  
        return rooms  
  
    def check_reservation_status(self, reservation_id: int) -> str:  
        print("check_reservation_status")  
        result = self.session.query(Reservation).filter_by(id=reservation_id, status="booked").first()  
        if result:  
            output = {  
                'reservation_id': result.id,  
                'customer_id': result.customer_id,  
                'room_type': result.room_type,  
                'hotel_id': result.hotel_id,  
                'check_in_date': result.check_in_date.strftime('%Y-%m-%d'),  
                'check_out_date': result.check_out_date.strftime('%Y-%m-%d'),  
                'status': result.status  
            }  
        else:  
            output = f"Cannot find status for the reservation with ID {reservation_id}"  
        return str(output)  
  
    def confirm_reservation_change(self, current_reservation_id: int, new_room_type: str, new_check_in_date: str, new_check_out_date: str) -> str:  
        charge = 50  
        old_reservation = self.session.query(Reservation).filter_by(id=current_reservation_id, status="booked").first()  
        if old_reservation:  
            old_reservation.status = "cancelled"  
            self.session.commit()  
            new_reservation_id = random.randint(100000, 999999)  
            new_reservation = Reservation(  
                id=new_reservation_id,  
                customer_id=old_reservation.customer_id,  
                hotel_id=old_reservation.hotel_id,  
                room_type=new_room_type,  
                check_in_date=datetime.strptime(new_check_in_date, '%Y-%m-%d'),  
                check_out_date=datetime.strptime(new_check_out_date, '%Y-%m-%d'),  
                status="booked"  
            )  
            self.session.add(new_reservation)  
            self.session.commit()  
            return (f"Your new reservation for a {new_room_type} room is confirmed. Check-in date is {new_check_in_date} "  
                    f"and check-out date is {new_check_out_date}. Your new reservation ID is {new_reservation_id}. "  
                    f"A charge of ${charge} has been applied for the change.")  
        else:  
            return "Could not find the current reservation to change."  
  
    def check_change_reservation(self, current_reservation_id: int, new_check_in_date: str, new_check_out_date: str, new_room_type: str) -> str:  
        charge = 50  
        return f"Changing your reservation will cost an additional ${charge}."  
  
    def load_user_reservation_info(self, user_id: str) -> str:  
        print("load_user_reservation_info")  
        matched_reservations = self.session.query(Reservation).filter_by(customer_id=user_id, status="booked").all()  
        reservations_info: List[Dict[str, Union[str, int]]] = [{  
            'room_type': reservation.room_type,  
            'hotel_id': reservation.hotel_id,  
            'check_in_date': reservation.check_in_date.strftime('%Y-%m-%d'),  
            'check_out_date': reservation.check_out_date.strftime('%Y-%m-%d'),  
            'reservation_id': reservation.id,  
            'status': reservation.status  
        } for reservation in matched_reservations]  
          
        return str(reservations_info) if reservations_info else "Sorry, we cannot find any reservation information for you."  