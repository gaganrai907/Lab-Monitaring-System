from datetime import datetime, timezone

from database import get_connection


def create_alert(
    device_id: str,
    alert_type: str,
    title: str,
    message: str,
    severity: str = "WARNING"
):
    """
    Create a new monitoring alert.
    """

    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        INSERT INTO alerts (
            device_id,
            alert_type,
            title,
            message,
            severity,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        device_id,
        alert_type,
        title,
        message,
        severity,
        "NEW",
        now
    ))

    alert_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return alert_id


def get_alerts(limit: int = 50):
    """
    Get latest monitoring alerts.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            alerts.id,
            alerts.device_id,
            pcs.lab_name,
            pcs.pc_number,
            alerts.alert_type,
            alerts.title,
            alerts.message,
            alerts.severity,
            alerts.status,
            alerts.created_at
        FROM alerts
        LEFT JOIN pcs
            ON alerts.device_id = pcs.device_id
        ORDER BY alerts.id DESC
        LIMIT ?
    """, (limit,))

    alerts = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return alerts