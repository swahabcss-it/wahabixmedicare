from django.db import models

# This app has no models of its own — it manages Clinic and StaffProfile
# records that belong to apps.core, scoped to the logged-in clinic admin's
# own clinic. Keeping it model-free avoids a second source of truth for
# tenant/staff data.
