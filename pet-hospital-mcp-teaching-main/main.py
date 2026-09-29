import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
 
app = FastAPI()
API_KEY = "KAQNJEM-G4942MJ-G4XB4S1-HARBQNQ6"
BASE_URL = "http://localhost:3001"
WORKSPACE_DIR = os.path.dirname(os.path.abspath(file))
 
class Question(BaseModel):
text: str
 
@app.post("/ask")
async def ask(question: Question):
workspace_path = os.path.join(WORKSPACE_DIR, "first_workspace.txt")
if not os.path.exists(workspace_path):
raise HTTPException(status_code=404, detail="Workspace file not found")
with open(workspace_path, 'r', encoding='utf-8') as f:
workspace_content = f.read()
payload = {"apikey": API_KEY, "question": question.text, "workspaceContent": workspace_content}
response = requests.post(f"{BASE_URL}/mcp/v2/ask", json=payload)
if response.status_code == 200:
return response.json()
raise HTTPException(status_code=response.status_code, detail="AI service error")
 
if name == "main":
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8080)