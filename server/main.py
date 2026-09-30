from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from alerts import create_alert, get_alerts
from config import SERVER_API_KEY, HEARTBEAT_TIMEOUT
from database import get_connection, init_database
from models import (
    PCRegisterRequest,
    HeartbeatRequest,
    UserCreateRequest
)

app = FastAPI(
    title="College Lab Monitoring Server",
    version="1.0.0"
)


@app.on_event("startup")
def startup():
    init_database()


def verify_api_key(api_key: str):
    if api_key != SERVER_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )


@app.get("/")
def home():
    return {
        "message": "College Lab Monitoring Server is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/api/pcs/register")
def register_pc(
    data: PCRegisterRequest,
    x_api_key: str = Header(...)
):
    verify_api_key(x_api_key)

    now = datetime.now(timezone.utc).isoformat()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM pcs
        WHERE device_id = ?
    """, (data.device_id,))

    existing_pc = cursor.fetchone()

    if existing_pc:

        cursor.execute("""
            UPDATE pcs
            SET
                lab_name = ?,
                pc_number = ?,
                hostname = ?,
                agent_version = ?,
                status = 'ONLINE',
                last_heartbeat = ?
            WHERE device_id = ?
        """, (
            data.lab_name,
            data.pc_number,
            data.hostname,
            data.agent_version,
            now,
            data.device_id
        ))

        connection.commit()
        connection.close()

        return {
            "success": True,
            "message": "PC already registered",
            "device_id": data.device_id
        }

    cursor.execute("""
        INSERT INTO pcs (
            lab_name,
            pc_number,
            device_id,
            hostname,
            status,
            last_heartbeat,
            agent_version,
            approved,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.lab_name,
        data.pc_number,
        data.device_id,
        data.hostname,
        "ONLINE",
        now,
        data.agent_version,
        1,
        now
    ))

    connection.commit()
    connection.close()

    return {
        "success": True,
        "message": "PC registered successfully",
        "device_id": data.device_id
    }


@app.post("/api/pcs/heartbeat")
def heartbeat(
    data: HeartbeatRequest,
    x_api_key: str = Header(...)
):
    verify_api_key(x_api_key)

    now = datetime.now(timezone.utc).isoformat()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM pcs
        WHERE device_id = ?
    """, (data.device_id,))

    pc = cursor.fetchone()

    if not pc:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="PC is not registered"
        )

    cursor.execute("""
        UPDATE pcs
        SET
            status = 'ONLINE',
            last_heartbeat = ?
        WHERE device_id = ?
    """, (
        now,
        data.device_id
    ))

    connection.commit()
    connection.close()

    return {
        "success": True,
        "status": "ONLINE",
        "time": now
    }


@app.get("/api/pcs")
def get_all_pcs(
    x_api_key: str = Header(...)
):
    verify_api_key(x_api_key)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            lab_name,
            pc_number,
            device_id,
            hostname,
            status,
            last_heartbeat,
            agent_version,
            approved
        FROM pcs
        ORDER BY lab_name, pc_number
    """)

    pcs = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return {
        "count": len(pcs),
        "pcs": pcs
    }

@app.post("/api/users")
def create_user(
    data: UserCreateRequest,
    x_api_key: str = Header(...)
):
    verify_api_key(x_api_key)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM users
        WHERE telegram_id = ?
    """, (data.telegram_id,))

    existing_user = cursor.fetchone()

    if existing_user:
        connection.close()

        raise HTTPException(
            status_code=409,
            detail="User already exists"
        )

    now = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        INSERT INTO users (
            telegram_id,
            name,
            username,
            role,
            assigned_lab,
            active,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.telegram_id,
        data.name,
        data.username,
        data.role,
        data.assigned_lab,
        1,
        now
    ))

    connection.commit()
    connection.close()

    return {
        "success": True,
        "message": "User created successfully",
        "telegram_id": data.telegram_id,
        "role": data.role
    }

@app.get("/api/users/{telegram_id}")
def get_user(
    telegram_id: str,
    x_api_key: str = Header(...)
):
    verify_api_key(x_api_key)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            telegram_id,
            name,
            username,
            role,
            assigned_lab,
            active
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,))

    user = cursor.fetchone()
    connection.close()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "success": True,
        "user": dict(user)
    }


@app.post("/api/alerts")
def create_alert_api(
    data: dict,
    x_api_key: str = Header(...)
):
    verify_api_key(x_api_key)

    required_fields = [
        "device_id",
        "alert_type",
        "title",
        "message"
    ]

    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing field: {field}"
            )

    alert_id = create_alert(
        device_id=data["device_id"],
        alert_type=data["alert_type"],
        title=data["title"],
        message=data["message"],
        severity=data.get("severity", "WARNING")
    )

    return {
        "success": True,
        "alert_id": alert_id,
        "message": "Alert created successfully"
    }


@app.get("/api/alerts")
def get_alerts_api(
    x_api_key: str = Header(...)
):
    verify_api_key(x_api_key)

    alerts = get_alerts()

    return {
        "count": len(alerts),
        "alerts": alerts
    }