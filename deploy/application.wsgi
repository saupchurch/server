# This file is copied into place by the .whiskey/action_hooks/pre-build hook during Docker build

from ga4gh.frontend import app as application
import ga4gh.frontend as frontend
frontend.configure("/srv/ga4gh/config.py")
