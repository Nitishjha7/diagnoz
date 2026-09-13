from workers.tasks.report_generate import generate_inspection_report

result = generate_inspection_report.apply(
    args=(
        "dispatch-test-1",
        {
            "session_id": "session-abc",
            "customer_name": "Cust One",
            "technician_name": "Tech One",
            "diagnosis_summary": "AC compressor rattling, MEDIUM urgency",
            "voice_transcript": "Mera AC cooling nahi kar raha...",
            "parts_replaced": [{"name": "Run Capacitor 45uF", "quantity": 1, "cost": 450}],
            "total_service_fee": 1000,
            "platform_commission_fee": 150,
            "technician_earnings": 841.5,
        },
        "/tmp/reports_out",
    )
).get()
print("RESULT:", result)
