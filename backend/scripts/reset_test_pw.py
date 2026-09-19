import bcrypt
from sqlalchemy import create_engine, text

pw = b"Test1234!"
hashed = bcrypt.hashpw(pw, bcrypt.gensalt(12)).decode("utf-8")
print(f"Generated hash: {hashed}")

# Verify
assert bcrypt.checkpw(pw, hashed.encode("utf-8"))
print("Self check passed!")

# Update DB
engine = create_engine("postgresql://voluuser:volupassword@volumeal-postgres:5432/volumeal")
with engine.begin() as conn:
    conn.execute(
        text("UPDATE users SET password_hash = :h WHERE email IN ('test@volumeal.io', 'admin@volumeal.io')"),
        {"h": hashed},
    )
print("Successfully updated test@volumeal.io and admin@volumeal.io passwords to Test1234!")
