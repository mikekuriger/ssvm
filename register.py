from __future__ import print_function, division, absolute_import
import sys

if sys.version_info < (2, 7):  # For Python 2.6 and earlier
    import register_26 as register
else:  # For Python 3 and later
    import register_3 as register

# Run the main function or entry point of the imported script
if hasattr(register, 'main'):
    register.main()

