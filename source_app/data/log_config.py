import logging, sys, os

def setup_logging(enable_logging: bool = True, log_file: str = "game.log", log_level=logging.INFO):
    if not enable_logging:
        logging.disable(logging.CRITICAL)
        return
    
    appimage_path = os.environ.get("APPIMAGE")
    if appimage_path:
        # Linux AppImage
        exe_path = os.path.dirname(appimage_path)
    elif getattr(sys, "frozen", False):
        # Normal PyInstaller exe
        exe_path = os.path.dirname(sys.executable)
    else:
        # Running from source
        exe_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    log_path = os.path.join(exe_path, log_file)

    logging.basicConfig(
        filename=str(log_path),
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    original_excepthook = sys.excepthook

    def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        original_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = log_uncaught_exceptions