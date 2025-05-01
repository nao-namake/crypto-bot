import subprocess
import sys

def test_run_main():
    # -m オプションで crypto_bot.main を起動
    res = subprocess.run([sys.executable, "-m", "crypto_bot.main"], check=True)
    assert res.returncode == 0