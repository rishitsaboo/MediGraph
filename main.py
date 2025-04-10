from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import db
from models import Disease, Symptom, Drug, SearchResult
import uvicorn

# Initialize FastAPI application
app = FastAPI(title="Medical Graph API")

# Enable CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Helper function to get disease data
def get_disease_data(tx, name: str):
    result = tx.run("""
    MATCH (d:Disease {name: $name})
    OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
    OPTIONAL MATCH (d)-[:TREATED_WITH]->(dr:Drug)
    RETURN d, collect(s) AS symptoms, collect(dr) AS drugs
    """, name=name)
    return result.single()

# Endpoint to get disease details
@app.get("/diseases/{disease_name}", response_model=Disease)
async def get_disease(disease_name: str):
    with db.get_session() as session:
        result = session.execute_read(get_disease_data, disease_name)
        if not result:
            raise HTTPException(status_code=404, detail="Disease not found")
        
        disease = result["d"]
        return Disease(
            name=disease["name"],
            type=disease.get("type"),
            symptoms=[Symptom(**s) for s in result["symptoms"]],
            drugs=[Drug(**dr) for dr in result["drugs"]]
        )

# Search endpoint
@app.get("/search", response_model=SearchResult)
async def search(query: str):
    with db.get_session() as session:
        result = session.run("""
        MATCH (n) 
        WHERE toLower(n.name) CONTAINS toLower($query)
        RETURN n, labels(n)[0] AS type
        """, query=query)
        
        diseases = []
        symptoms = []
        drugs = []
        
        for record in result:
            node = record["n"]
            node_type = record["type"]
            
            if node_type == "Disease":
                diseases.append(Disease(
                    name=node["name"],
                    type=node.get("type")
                ))
            elif node_type == "Symptom":
                symptoms.append(Symptom(
                    name=node["name"],
                    severity=node.get("severity")
                ))
            elif node_type == "Drug":
                drugs.append(Drug(
                    name=node["name"],
                    type=node.get("type")
                ))
        
        return SearchResult(
            query=query,
            diseases=diseases,
            symptoms=symptoms,
            drugs=drugs
        )

# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)