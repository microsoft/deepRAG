import unittest
from langserve.client import RemoteRunnable

class LangServeTests(unittest.TestCase):
    def setUp(self):
        # Set up the Langchain client and connect to the local server
        self.client = RemoteRunnable("http://localhost:8000/vectorRAG")

    def test_server_response(self) -> None:
        # Test a specific server response
        response = self.client.invoke(input="What is a vector?")  # Replace with your API endpoint
        self.assertIsNotNone(response)  # Replace with the expected status code

    # Add more test methods as needed

if __name__ == '__main__':
    unittest.main()