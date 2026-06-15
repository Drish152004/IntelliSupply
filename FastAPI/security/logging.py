import logging
from security.pii import mask_pii

class PIIMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_pii(record.msg)

        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    new_args.append(mask_pii(arg))
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)

        return True

def setup_secure_logging():
    """Apply the PII masking logging filter to the root logger to secure all log outputs."""
    root_logger = logging.getLogger()
    pii_filter = PIIMaskingFilter()

    # Check if filter has already been added to avoid duplicates
    for f in root_logger.filters:
        if isinstance(f, PIIMaskingFilter):
            return

    root_logger.addFilter(pii_filter)
