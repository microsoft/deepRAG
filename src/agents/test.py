import asyncio
import sys
sys.path.append('..')
import yaml
async def main():
    with open("agent_profiles/hotel_agent_profile.yaml", 'r') as file:  
        data = yaml.safe_load(file) 
        print(data["name"]) 

    

if __name__ == "__main__":  
    asyncio.run(main())  
