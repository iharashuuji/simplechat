# lambda/index.py
import json
import os
import re
import urllib.request
import urllib.error  # エラーハンドリング用

# ngrokで公開したFastAPIエンドポイント
NGROK_URL = "https://059f-34-125-46-83.ngrok-free.app/generate"  # ★ここにあなたのURLを貼り付けてください

# Lambda コンテキストからリージョンを抽出する関数（使わないけど残しておいてOK）
def extract_region_from_arn(arn):
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Cognitoで認証されたユーザー情報の取得（必要に応じて）
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['prompt'] # もともとbody["message"]
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)

        # 会話履歴を構築
        messages = conversation_history.copy()
        messages.append({
            "role": "user",
            "content": message
        })
        
        # FastAPI用に整形したリクエスト形式（例：OpenAI chat形式に近い構造）
        request_payload = {
        "prompt": message,
        "max_new_tokens": 512,
        "do_sample": True,
        "temperature": 0.7,
        "top_p": 0.9
        }

        print("Calling ngrok FastAPI endpoint with payload:", json.dumps(request_payload))

        # FastAPIへリクエスト送信
        req = urllib.request.Request(
            NGROK_URL,
            data=json.dumps(request_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req) as res:
            response_body = json.loads(res.read().decode('utf-8'))

        print("Ngrok FastAPI response:", json.dumps(response_body))

        # 応答の取得（FastAPIが {"response": "..."} を返す前提）
        assistant_response = response_body.get("generated_text")
        if not assistant_response:
            raise Exception("No response content from FastAPI model")

        # 応答を履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })

        # 成功レスポンス
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
            "generated_text": assistant_response,
            "response_time": 0
            })
        }

    except urllib.error.HTTPError as e:
        print("HTTPError:", e.code, e.reason)
        return {
            "statusCode": e.code,
            "body": json.dumps({"success": False, "error": e.reason})
        }

    except Exception as error:
        print("Error:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
