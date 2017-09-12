import pytest, os
from src import reserveQAStack 

class TestReserveQAStack:
    token = None
    
    def test_setup(self):
        self.token = os.environ.get("TOKEN")
        assert self.token != None, "Token is not set, skip"

    def test_datafile(self):           
        data_file = os.getenv("DATA_FILE", "../topics.json")
        assert data_file != None
        
    def test_tieout(self):           
        data_file = os.getenv("TIMEOUT", "7200")
        assert data_file == "7200", "No timeout set"
            
    def test_users(self):   
        bot = reserveQAStack.QASlackBot()
        assert bot != None, "QASlackBot() not initialized"