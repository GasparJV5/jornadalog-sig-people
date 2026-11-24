from datetime import datetime, timedelta
from src.domain.allocation_rules import validate_allocation
def test_blocks_insufficient_rest():
    start=datetime.now(); r=validate_allocation({'active':True},{'valid':True},True,start-timedelta(hours=8),start,11)
    assert r['resultado']=='BLOQUEADO'
def test_allows_valid():
    start=datetime.now(); r=validate_allocation({'active':True},{'valid':True},True,start-timedelta(hours=12),start,11)
    assert r['resultado']=='APTO'
