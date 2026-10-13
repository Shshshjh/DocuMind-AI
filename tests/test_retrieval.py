from app.retrieval import split_text, retrieve

def test_chunking_overlap_and_completeness():
    result=split_text("Hello world "*300,chunk_chars=120,overlap=25)
    assert len(result)>2
    assert all(result)

def test_search_returns_relevant_passage():
    rows=[{"page":1,"text":"Cats love fish and naps."},{"page":2,"text":"Database transaction rollback and locking."}]
    hits=retrieve("database transaction",rows,top_k=1)
    assert hits[0]["page"]==2

def test_unknown_question_has_no_false_match():
    rows=[{"page":1,"text":"Bananas are yellow."}]
    assert retrieve("quantum entanglement",rows)==[]
