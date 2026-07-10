import subprocess
subprocess.run([
    "git", "add", "-A"
], shell=False, cwd=r"C:\Users\Administrator\.openclaw\workspace\skills\automated-news-push")
subprocess.run([
    "git", "commit", "-m", "v0.6: 6项升级 - 恐惧贪婪指数+收藏+原文链接+CoinDesk+Decrypt+手机优化"
], shell=False, cwd=r"C:\Users\Administrator\.openclaw\workspace\skills\automated-news-push")
subprocess.run([
    "git", "push", "-u", "origin", "master"
], shell=False, cwd=r"C:\Users\Administrator\.openclaw\workspace\skills\automated-news-push")
print("✅ Git push done")
