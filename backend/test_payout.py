from workers.tasks.payout_settle import settle_weekly_payouts

result = settle_weekly_payouts.apply().get()
print("RESULT:", result)
