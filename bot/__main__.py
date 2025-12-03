import logging

from .telegram_bot import run_bot


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_bot()


if __name__ == "__main__":
    main()
