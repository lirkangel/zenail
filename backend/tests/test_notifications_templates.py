from app.notifications.templates import render


def test_email_template_splits_subject_and_body():
    subject, body = render(
        "reminder_24h.guest.email",
        "vi",
        {
            "client_name": "An",
            "branch_name": "Zenail Central",
            "master_name": "Linh",
            "procedures": ["Manicure"],
            "start_local": "10:00 09/05/2026",
            "booking_reference": "ABC123",
        },
    )
    assert subject == "[Zenail] Nhắc lịch ngày mai"
    assert "An" in body
    assert "ABC123" in body


def test_sms_template_returns_no_subject():
    subject, body = render(
        "reminder_24h.guest.sms",
        "vi",
        {
            "client_name": "An",
            "branch_name": "Zenail Central",
            "master_name": "Linh",
            "procedures": ["Manicure"],
            "start_local": "10:00 09/05/2026",
            "booking_reference": "ABC123",
        },
    )
    assert subject is None
    assert "ABC123" in body
