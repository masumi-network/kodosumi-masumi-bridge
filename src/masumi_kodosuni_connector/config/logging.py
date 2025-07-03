import structlog
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
from masumi_kodosuni_connector.config.settings import settings


class LogConfig:
    """Centralized logging configuration"""
    
    def __init__(self):
        self.project_root = self._get_project_root()
        self.logs_dir = self.project_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        # Log file paths
        self.main_log = self.logs_dir / "masumi_connector.log"
        self.flow_log = self.logs_dir / "flow_submissions.log"
        self.payment_log = self.logs_dir / "payments.log"
        self.kodosumi_log = self.logs_dir / "kodosumi_api.log"
        self.error_log = self.logs_dir / "errors.log"
        
        # Log levels
        self.log_level = logging.DEBUG if settings.debug else logging.INFO
        self.file_log_level = logging.DEBUG  # Always debug for files
        
        # Formatters
        self.detailed_formatter = logging.Formatter(
            '%(asctime)s | %(name)-20s | %(levelname)-8s | %(funcName)-20s:%(lineno)-4d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.simple_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.json_formatter = structlog.processors.JSONRenderer()
    
    def _get_project_root(self) -> Path:
        """Get the project root directory"""
        current_file = Path(__file__).resolve()
        # Navigate up from src/masumi_kodosuni_connector/config/logging.py to project root
        return current_file.parent.parent.parent.parent
    
    def create_rotating_handler(self, filepath: Path, max_bytes: int = 10*1024*1024, backup_count: int = 5) -> logging.Handler:
        """Create a rotating file handler with proper configuration"""
        handler = logging.handlers.RotatingFileHandler(
            filepath,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        handler.setLevel(self.file_log_level)
        handler.setFormatter(self.detailed_formatter)
        return handler
    
    def create_console_handler(self) -> logging.Handler:
        """Create console handler for stdout"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.log_level)
        
        # Use simple format for console in production, detailed in debug
        formatter = self.detailed_formatter if settings.debug else self.simple_formatter
        handler.setFormatter(formatter)
        return handler
    
    def create_error_handler(self) -> logging.Handler:
        """Create handler specifically for error logs"""
        handler = logging.handlers.RotatingFileHandler(
            self.error_log,
            maxBytes=5*1024*1024,
            backupCount=10,
            encoding='utf-8'
        )
        handler.setLevel(logging.ERROR)
        handler.setFormatter(self.detailed_formatter)
        return handler


def setup_logger(name: str, log_file: Optional[Path] = None, level: Optional[int] = None) -> logging.Logger:
    """Setup a logger with standard configuration"""
    config = LogConfig()
    logger = logging.getLogger(name)
    
    # Clear any existing handlers
    logger.handlers.clear()
    logger.setLevel(level or config.log_level)
    
    # Add console handler
    logger.addHandler(config.create_console_handler())
    
    # Add file handler if specified
    if log_file:
        logger.addHandler(config.create_rotating_handler(log_file))
    
    # Add error handler for all loggers
    logger.addHandler(config.create_error_handler())
    
    # Prevent duplicate logs
    logger.propagate = False
    
    return logger


def configure_logging():
    """Configure comprehensive logging for the entire application"""
    config = LogConfig()
    
    # Remove any existing handlers from root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Configure root logger
    root_logger.setLevel(config.log_level)
    root_logger.addHandler(config.create_console_handler())
    root_logger.addHandler(config.create_rotating_handler(config.main_log))
    root_logger.addHandler(config.create_error_handler())
    
    # Configure specialized loggers
    setup_specialized_loggers(config)
    
    # Configure structlog
    configure_structlog(config)
    
    # Log startup message
    logger = structlog.get_logger("logging")
    logger.info("Logging system initialized", 
                log_level=logging.getLevelName(config.log_level),
                logs_directory=str(config.logs_dir),
                main_log=str(config.main_log),
                debug_mode=settings.debug)


def setup_specialized_loggers(config: LogConfig):
    """Setup specialized loggers for different components"""
    
    # Flow submission logger
    flow_logger = logging.getLogger("flow_submission")
    flow_logger.handlers.clear()
    flow_logger.setLevel(logging.DEBUG)
    flow_logger.addHandler(config.create_rotating_handler(config.flow_log))
    flow_logger.addHandler(config.create_console_handler())
    flow_logger.addHandler(config.create_error_handler())
    flow_logger.propagate = False
    
    # Payment logger
    payment_logger = logging.getLogger("payment")
    payment_logger.handlers.clear()
    payment_logger.setLevel(logging.DEBUG)
    payment_logger.addHandler(config.create_rotating_handler(config.payment_log))
    payment_logger.addHandler(config.create_console_handler())
    payment_logger.addHandler(config.create_error_handler())
    payment_logger.propagate = False
    
    # Kodosumi API logger
    kodosumi_logger = logging.getLogger("kodosumi")
    kodosumi_logger.handlers.clear()
    kodosumi_logger.setLevel(logging.DEBUG)
    kodosumi_logger.addHandler(config.create_rotating_handler(config.kodosumi_log))
    kodosumi_logger.addHandler(config.create_console_handler())
    kodosumi_logger.addHandler(config.create_error_handler())
    kodosumi_logger.propagate = False
    
    # Database logger
    db_logger = logging.getLogger("database")
    db_logger.handlers.clear()
    db_logger.setLevel(logging.INFO)  # Less verbose for DB
    db_logger.addHandler(config.create_rotating_handler(config.main_log))
    db_logger.addHandler(config.create_error_handler())
    db_logger.propagate = False
    
    # Polling service logger
    polling_logger = logging.getLogger("polling")
    polling_logger.handlers.clear()
    polling_logger.setLevel(logging.INFO)
    polling_logger.addHandler(config.create_rotating_handler(config.main_log))
    polling_logger.addHandler(config.create_console_handler())
    polling_logger.addHandler(config.create_error_handler())
    polling_logger.propagate = False


def configure_structlog(config: LogConfig):
    """Configure structlog with proper processors"""
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add appropriate renderer based on environment
    if settings.debug:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structlog logger for the given name"""
    return structlog.get_logger(name)


def log_function_call(logger: structlog.BoundLogger, func_name: str, **kwargs):
    """Helper to log function calls with parameters"""
    logger.debug(f"Function called: {func_name}", **kwargs)


def log_function_result(logger: structlog.BoundLogger, func_name: str, result_type: str, **kwargs):
    """Helper to log function results"""
    logger.debug(f"Function completed: {func_name}", result_type=result_type, **kwargs)