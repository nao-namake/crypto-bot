from setuptools import find_packages, setup

setup(
    name="crypto_bot",
    version="0.1.0",
    description="汎用暗号資産トレーディングボット",
    author="あなたの名前",
    author_email="you@example.com",
    url="https://github.com/あなたのID/crypto-bot",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(include=["crypto_bot", "crypto_bot.*"]),
    python_requires=">=3.11, <3.13",
    install_requires=[
        # データ操作
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        # 機械学習
        "optuna>=3.0.0",
        "scikit-learn>=1.2.0",
        "lightgbm>=4.0.0",
        # 設定読み込み
        "PyYAML>=6.0.0",
        # 取引所接続
        "ccxt>=2.10.0",
        # リアルタイムストリーミング
        "websockets>=11.0.0",
        # リトライ
        "tenacity>=8.2.0",
        # .env 自動読み込み
        "python-dotenv>=1.0.0",
        # CLI
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "crypto-bot=crypto_bot.main:cli",
        ],
    },
)
