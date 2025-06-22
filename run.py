#!/usr/bin/env python3

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now we can import and run the application
if __name__ == "__main__":
    from masumi_kodosuni_connector.main import main
    main()