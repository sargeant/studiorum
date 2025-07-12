Installation
============

This guide covers how to install and set up 5e2pdf on your system.

Requirements
------------

- Python 3.11 or higher
- LaTeX distribution (for PDF compilation)
- Git (for cloning 5etools data)

Python Installation
-------------------

5e2pdf requires Python 3.11 or higher. You can download Python from the official website:

https://www.python.org/downloads/

Installing 5e2pdf
------------------

Via pip (Recommended)
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install 5e2pdf

From Source
~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/your-repo/5e2pdf.git
   cd 5e2pdf
   pip install -e .

LaTeX Installation
------------------

For PDF compilation, you'll need a LaTeX distribution with XeLaTeX support.

macOS
~~~~~

.. code-block:: bash

   # Using Homebrew
   brew install --cask mactex

   # Or using MacPorts
   sudo port install texlive-xetex

Ubuntu/Debian
~~~~~~~~~~~~~

.. code-block:: bash

   sudo apt-get update
   sudo apt-get install texlive-xetex texlive-fonts-recommended

Windows
~~~~~~~

Download and install MiKTeX from:

https://miktex.org/download

Setting Up Data Sources
------------------------

5e2pdf works with JSON data from the 5etools project. You'll need to clone their data repository:

.. code-block:: bash

   # Clone the 5etools data repository
   git clone https://github.com/5etools-mirror-3/5etools-src.git

   # Create a symlink to the data directory
   ln -s ../5etools-src/data data

Alternatively, you can specify custom data paths in your configuration.

Verification
------------

To verify your installation, run:

.. code-block:: bash

   5e2pdf --version
   5e2pdf --help

You should see version information and help text if everything is installed correctly.

Configuration
-------------

5e2pdf uses a configuration file for default settings. You can create one at:

- Linux/macOS: ``~/.config/5e2pdf/config.yaml``
- Windows: ``%APPDATA%\\5e2pdf\\config.yaml``

Example configuration:

.. code-block:: yaml

   data_paths:
     - "./data"
     - "./homebrew"
   
   output:
     default_directory: "./output"
     include_images: false
   
   latex:
     engine: "xelatex"
     additional_packages: []

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**ImportError: No module named 'pydantic'**

This usually means the installation didn't complete properly. Try:

.. code-block:: bash

   pip install --upgrade 5e2pdf

**LaTeX compilation fails**

Make sure you have XeLaTeX installed and available in your PATH:

.. code-block:: bash

   which xelatex

**No data found**

Ensure you've cloned the 5etools data repository and created the symlink:

.. code-block:: bash

   ls -la data/

You should see directories like ``adventure/``, ``book/``, etc.

Getting Help
~~~~~~~~~~~~

If you encounter issues:

1. Check the troubleshooting section in this documentation
2. Search existing issues on GitHub
3. Create a new issue with detailed error messages and your system information