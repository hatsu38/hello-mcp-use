from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from langchain_anthropic import ChatAnthropic
from mcp_use import MCPAgent, MCPClient
import os
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()

# FastAPIアプリケーションを初期化
app = FastAPI(title="MCP Agent API", version="1.0.0")

# リクエストモデル
class QueryRequest(BaseModel):
    query: str
    
# レスポンスモデル
class QueryResponse(BaseModel):
    result: str
    status: str

# MCPエージェントをグローバルに初期化（起動時に一度だけ）
agent = None

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時にMCPエージェントを初期化"""
    global agent
    try:
        # MCPクライアントを設定
        client = MCPClient.from_config_file(
            os.path.join("browser_mcp.json")
        )
        
        # LLMを初期化
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620", 
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # エージェントを初期化
        agent = MCPAgent(llm=llm, client=client)
        print("✅ MCP Agent initialized successfully!")
        
    except Exception as e:
        print(f"❌ Failed to initialize MCP Agent: {e}")
        raise e

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """クエリを処理してMCPエージェントに実行させる"""
    global agent
    
    if agent is None:
        raise HTTPException(status_code=500, detail="MCP Agent not initialized")
    
    try:
        # エージェントを実行
        result = await agent.run(request.query)
        
        return QueryResponse(
            result=result,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing query: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "agent_ready": agent is not None}

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "MCP Agent API", 
        "version": "1.0.0",
        "endpoints": {
            "POST /query": "Process queries with MCP Agent",
            "GET /health": "Health check",
            "GET /docs": "API documentation"
        }
    }

if __name__ == "__main__":
    # 開発用サーバーを起動
    uvicorn.run(
        "main:app",  # ファイル名がmain.pyの場合
        host="0.0.0.0",
        port=8000,
        reload=True
    )
