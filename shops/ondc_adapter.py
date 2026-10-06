import logging

from django.conf import settings
from django.utils.module_loading import import_string


logger = logging.getLogger(__name__)


def check_participant_connection(enrollment):
    """Run the configured Seller Network Participant adapter's safe health check.

    The participant chooses its own transport and protocol. The adapter must
    return the boolean True only after it confirms a successful authenticated
    connection. Credentials belong in the deployment secret store, not here.
    """
    adapter_path = getattr(settings, 'ONDC_PARTICIPANT_ADAPTER', '').strip()
    if not adapter_path:
        return 'not_configured', 'No participant-specific integration adapter is configured yet.'

    try:
        adapter_class = import_string(adapter_path)
        adapter = adapter_class()
        connected = adapter.check_connection(enrollment)
    except Exception as exc:
        # Avoid returning provider exception text because it may contain secrets.
        logger.warning('ONDC participant connection check raised %s.', type(exc).__name__)
        return 'failed', 'Connection check failed. Review adapter configuration and server logs.'

    if connected is True:
        return 'connected', 'The configured participant adapter confirmed the connection.'
    return 'failed', 'The configured participant adapter did not confirm the connection.'
