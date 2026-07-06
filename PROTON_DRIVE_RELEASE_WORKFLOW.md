# Proton Drive Release Workflow

Use this workflow when publishing or updating installer downloads for the software store.

1. Build the Windows installer.
2. Upload installer to Proton Drive.
3. Create shareable Proton Drive link.
4. Optional: set password or expiry in Proton Drive.
5. Copy the Proton Drive link.
6. Open Django admin.
7. Create or update `SoftwareProduct`.
8. Paste Proton Drive link into `proton_drive_link` field.
9. Update version and release notes.
10. Save.
11. Customers with paid orders can access download page.

The website does not integrate directly with the Proton Drive API. It stores the share link and only exposes it after a customer has a paid order and active license.
