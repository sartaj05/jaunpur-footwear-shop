# ONDC Seller Network Participant adapter

The project keeps ONDC seller onboarding and a catalog snapshot separate from the participant-specific network protocol. To enable a connection check, implement a Python class and set `ONDC_PARTICIPANT_ADAPTER` to its import path, for example `your_integration.ondc.Adapter`.

The adapter class must have a no-argument constructor and this method:

```python
def check_connection(self, enrollment) -> bool:
    ...
```

Return the literal boolean `True` only after a successful authenticated check against the selected Seller Network Participant. Return `False` when the participant does not confirm the connection. The site records a generic result and does not display adapter exception text, since provider errors can contain credentials or other sensitive information.

The adapter owns the participant's documented transport, signatures, API version, and response validation. Read credentials from the deployment's secret manager or environment. Do not store keys or tokens in `ONDCEnrollment`, seller-controlled form fields, logs, or the repository. Use HTTPS and verify TLS certificates. Keep request timeouts bounded.

The default project configuration leaves this setting empty. In that state, the seller page explains that no network request is sent, and no connection check is offered. The hook only checks participant connectivity. Catalog publishing, inventory/order synchronization, payment settlement, network registration, and production certification still need implementation and approval for the chosen participant.
