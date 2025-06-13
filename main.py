from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
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
class UpdatedQueryResponse(BaseModel):
    result: List[Dict[str, Any]] | str
    status: str

# MCPエージェントをグローバルに初期化（起動時に一度だけ）
agent = None

security = HTTPBearer()
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.scheme != "Bearer" or credentials.credentials != API_BEARER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )

@app.on_event("startup")
async def startup_event():
    load_dotenv()
    
    """アプリケーション起動時にMCPエージェントを初期化"""
    global agent
    try:
        # MCPクライアントを設定
        # client = MCPClient.from_config_file(
        #     os.path.join("browser_mcp.json")
        # )
        config = {
            "mcpServers": {
                "notionApi": {
                    "command": "npx",
                    "args": ["-y", "@notionhq/notion-mcp-server"],
                    "env": {
                        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer " + os.getenv("NOTION_API_KEY") + "\", \"Notion-Version\": \"2022-06-28\" }"
                    }
                },
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
                    }
                },
                "slack": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-slack"
                    ],
                    "env": {
                        "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN"),
                        "SLACK_TEAM_ID": os.getenv("SLACK_TEAM_ID"),
                        "SLACK_CHANNEL_IDS": os.getenv("SLACK_CHANNEL_IDS")
                    }
                },
            }
        }

        # Create MCPClient from configuration dictionary
        client = MCPClient.from_dict(config)
        # LLMを初期化
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0,
            max_tokens=8192,
            timeout=None,
            max_retries=2,
        )
        # llm = ChatGoogleGenerativeAI(
        #     model="gemini-2.5-flash-preview-05-20",
        #     google_api_key=os.getenv("GEMINI_API_KEY"),
        #     temperature=0,
        #     max_tokens=None,
        #     timeout=None,
        #     max_retries=2,
        # )
        
        # エージェントを初期化
        agent = MCPAgent(llm=llm, client=client, use_server_manager=True, max_steps=50)
        print("✅ MCP Agent initialized successfully!")
        
    except Exception as e:
        print(f"❌ Failed to initialize MCP Agent: {e}")
        raise e

@app.post("/query", response_model=UpdatedQueryResponse)
async def process_query(
    request: QueryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    print("================")
    print(request.query)
    print("================")
    verify_token(credentials)
    global agent
    
    if agent is None:
        raise HTTPException(status_code=500, detail="MCP Agent not initialized")
    
    try:
        new_query = request.query + "\n\nLanguage Preference: You should always speak and think in the \"日本語\" (ja) language."
        # エージェントを実行
        result = await agent.run(new_query)
        print("================")
        print(f"result: {result}")
        print("================")
        # [type=list_type, input_value='Slackの最近の投稿...ルを探します。', input_type=str]
        return UpdatedQueryResponse(
            result=result,
            status="success"
        )
        
    except Exception as e:
        print("================")
        print(e)
        print("================")
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
