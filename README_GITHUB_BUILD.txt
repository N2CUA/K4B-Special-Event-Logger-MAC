K4B SPECIAL EVENT LOGGER 2.0.4 - GITHUB MAC BUILD
=================================================

This folder is ready to put in a GitHub repository and build with GitHub Actions.
Nothing in this package requires the ChatGPT/GitHub connector.

WHAT GITHUB BUILDS
------------------
The workflow .github/workflows/build-macos-intel.yml uses a fresh GitHub-hosted
Intel Mac runner and creates:

  K4B Special Event Logger.app

It then packages that application as:

  K4B_Special_Event_Logger_v2.0.4_macOS_Intel.zip

The downloadable GitHub artifact also contains:

  BUILD_INSPECTION.txt
  BUILD_SHA256.txt

BUILD_INSPECTION.txt records the runner/Python/PyInstaller information, verifies
that the .app bundle and executable exist, identifies the executable architecture,
shows the bundle identifier, reports the Mach-O macOS build/minimum-version data,
and lists the important bundle contents.

The workflow also ad-hoc signs the app and verifies bundle integrity. This is NOT
Apple Developer notarization; it is local integrity signing only.

HOW TO START THE BUILD ON GITHUB
--------------------------------
1. Create a GitHub repository and put the CONTENTS of this folder at repository root.
   The hidden .github folder must be included.
2. Open the repository's Actions tab.
3. Select "Build K4B Mac App".
4. Choose "Run workflow".
5. When the job completes, download the artifact named:

      K4B-Special-Event-Logger-macOS-Intel

6. Give BUILD_INSPECTION.txt and the finished Mac ZIP back to Randy/Sam for review
   before Jamie runs the app.

IMPORTANT COMPATIBILITY NOTE
----------------------------
Jamie's exact macOS version is still useful. The cloud build records the minimum
macOS version encoded in the finished executable. Review BUILD_INSPECTION.txt before
assuming the app is compatible with an older 2014 MacBook Air installation.

SECURITY / TRANSPARENCY
-----------------------
- The workflow uses GitHub's Intel macOS hosted runner.
- The GitHub actions referenced are official actions: checkout, setup-python,
  and upload-artifact.
- PyInstaller is pinned to 6.22.3 and downloaded from the official PyPI index.
- No account passwords or repository secrets are needed by this workflow.
- The job permission is read-only for repository contents.
- The source files remain plain text and can be inspected before the build.
