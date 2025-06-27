import structlog
import logging
import os
from masumi_kodosuni_connector.config.settings import settings


def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(message)s"
    )
    
    # Create flow submission logger with separate file handler
    flow_logger = logging.getLogger("flow_submission")
    flow_logger.setLevel(logging.DEBUG)
    
    # Create file handler for flow submissions
    flow_log_file = "flow_submissions.log"
    flow_handler = logging.FileHandler(flow_log_file)
    flow_handler.setLevel(logging.DEBUG)
    
    # Create formatter for flow logs
    flow_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    flow_handler.setFormatter(flow_formatter)
    
    # Add handler to flow logger
    flow_logger.addHandler(flow_handler)
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )