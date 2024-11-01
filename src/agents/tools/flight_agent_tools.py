import os  
import random  
from datetime import datetime, timedelta  
from typing import List, Dict, Union, Tuple
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey  
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker, relationship  
from dateutil import parser  
from .tools import Tool  
import json
Base = declarative_base()  

class Customer(Base):  
    __tablename__ = 'customers'  
    id = Column(String, primary_key=True)  
    name = Column(String)  
    flights = relationship('Flight', backref='customer')  
  
class Flight(Base):  
    __tablename__ = 'flights'  
    id = Column(Integer, primary_key=True, autoincrement=True)  
    customer_id = Column(String, ForeignKey('customers.id'))  
    ticket_num = Column(String)  
    flight_num = Column(String)  
    airline = Column(String)  
    seat_num = Column(String)  
    departure_airport = Column(String)  
    arrival_airport = Column(String)  
    departure_time = Column(DateTime)  
    arrival_time = Column(DateTime)  
    ticket_class = Column(String)  
    gate = Column(String)  
    status = Column(String)  
  
  
def transfer_conversation(user_request: str) -> str:  
    print("transfer_conversation!", user_request)  
    return f"{user_request}"  
  
class FlightAgentTool(Tool):  
    def __init__(self):  
        super().__init__()
        emb_map_file_path=os.getenv("FLIGHT_POLICY_FILE")  
        with open(emb_map_file_path) as file:  
            self.chunks_emb = json.load(file)  

        engine = create_engine(f'sqlite:///{os.getenv("FLIGHT_DB_FILE", "../data/flight_db.db")}')  
        Base.metadata.create_all(engine)  
        Session = sessionmaker(bind=engine)  
        self.session = Session()  
  
    def search_airline_knowledgebase(self, search_query: str) -> str:  
        return self.search_knowledge_base(search_query, topk=3)  
  
    def query_flights(self, from_: str, to: str, departure_time: str) -> str:  
        print("query_flights")  
  
        def get_new_times(departure_time: str, delta: int) -> Tuple[str, str]:  
            dp_dt = parser.parse(departure_time)  
            new_dp_dt = dp_dt + timedelta(hours=delta)  
            new_ar_dt = new_dp_dt + timedelta(hours=2)  
            return new_dp_dt.strftime("%Y-%m-%dT%H:%M:%S"), new_ar_dt.strftime("%Y-%m-%dT%H:%M:%S")  
  
        flights = ""  
        for flight_num, delta in [("AA479", -1), ("AA490", -2), ("AA423", -3)]:  
            new_departure_time, new_arrival_time = get_new_times(departure_time, delta)  
            flights += (f"flight number {flight_num}, from: {from_}, to: {to}, "  
                        f"departure_time: {new_departure_time}, arrival_time: {new_arrival_time}, "  
                        f"flight_status: on time\n")  
        return flights  
  
    def check_flight_status(self, flight_num: str, from_: str) -> str:  
        print("check_flight_status")  
        result = self.session.query(Flight).filter_by(flight_num=flight_num, departure_airport=from_, status="open").first()  
        if result:  
            output = {  
                'flight_num': result.flight_num,  
                'departure_airport': result.departure_airport,  
                'arrival_airport': result.arrival_airport,  
                'departure_time': result.departure_time.strftime('%Y-%m-%d %H:%M'),  
                'arrival_time': result.arrival_time.strftime('%Y-%m-%d %H:%M'),  
                'status': result.status  
            }  
        else:  
            output = f"Cannot find status for the flight {flight_num} from {from_}"  
        return str(output)  
  
    def confirm_flight_change(self, current_ticket_number: str, new_flight_number: str, new_departure_time: str, new_arrival_time: str) -> str:  
        charge = 80  
        old_flight = self.session.query(Flight).filter_by(ticket_num=current_ticket_number, status="open").first()  
        if old_flight:  
            old_flight.status = "cancelled"  
            self.session.commit()  
            new_ticket_num = str(random.randint(1000000000, 9999999999))  
            new_flight = Flight(  
                id=new_ticket_num,  
                ticket_num=new_ticket_num,  
                customer_id=old_flight.customer_id,  
                flight_num=new_flight_number,  
                seat_num=old_flight.seat_num,  
                airline=old_flight.airline,  
                departure_airport=old_flight.departure_airport,  
                arrival_airport=old_flight.arrival_airport,  
                departure_time=datetime.strptime(new_departure_time, '%Y-%m-%d %H:%M'),  
                arrival_time=datetime.strptime(new_arrival_time, '%Y-%m-%d %H:%M'),  
                ticket_class=old_flight.ticket_class,  
                gate=old_flight.gate,  
                status="open"  
            )  
            self.session.add(new_flight)  
            self.session.commit()  
            return (f"Your new flight now is {new_flight_number} departing from {new_flight.departure_airport} "  
                    f"to {new_flight.arrival_airport}. Your new departure time is {new_departure_time} and arrival time is {new_arrival_time}. "  
                    f"Your new ticket number is {new_ticket_num}. Your credit card has been charged with an amount of ${charge} dollars for fare difference.")  
        else:  
            return "Could not find the current ticket to change."  
  
    def check_change_booking(self, current_ticket_number: str, current_flight_number: str, new_flight_number: str, from_: str) -> str:  
        charge = 80  
        return f"Changing your ticket from {current_flight_number} to new flight {new_flight_number} departing from {from_} would cost {charge} dollars."  
  
    def load_user_flight_info(self, user_id: str) -> str:  
        print("load_user_flight_info")  
        matched_flights = self.session.query(Flight).filter_by(customer_id=user_id, status="open").all()  
        flights_info: List[Dict[str, Union[str, int]]] = [{  
            'airline': flight.airline,  
            'flight_num': flight.flight_num,  
            'seat_num': flight.seat_num,  
            'departure_airport': flight.departure_airport,  
            'arrival_airport': flight.arrival_airport,  
            'departure_time': flight.departure_time.strftime('%Y-%m-%d %H:%M'),  
            'arrival_time': flight.arrival_time.strftime('%Y-%m-%d %H:%M'),  
            'ticket_class': flight.ticket_class,  
            'ticket_num': flight.ticket_num,  
            'gate': flight.gate,  
            'status': flight.status  
        } for flight in matched_flights]  
          
        return str(flights_info) if flights_info else "Sorry, we cannot find any flight information for you."  