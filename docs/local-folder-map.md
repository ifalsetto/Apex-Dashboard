# Local Folder Map

## Active beta

```text
C:\FalseTech\Beta\Apex Dashboard
```

Use this folder for the public beta branch and local validation.

## Reports

```text
C:\FalseTech\Reports\Apex Cleanup
```

Use this folder for inventory reports and final cleanup reports.

## Archives

```text
C:\FalseTech\Archives\Apex Dashboard
```

Use this folder for timestamped archives of contaminated or stale beta folders. Do not permanently delete old work.

## Backups

```text
C:\FalseTech\Backups\Apex Dashboard
```

Use this folder before any risky recovery operation. A hard reset must not be run unless a timestamped backup exists and the final report explains why.

## Messy development repo

```text
C:\FalseTech\Projects\Apex-Dashboard
```

This folder can keep old local experiments and uncommitted work. Do not use it as the public beta release folder.

## Old contaminated path

Do not reference the older nested Apex project folder from the beta. If a legacy absolute project path appears in source, docs, env files, scripts, or configs, replace the reference with the clean beta path or remove it when obsolete.

## User profile FalseTech folder

```text
C:\Users\andre\FalseTech
```

Use as historical reference only unless a specific file is intentionally migrated into the clean beta branch.
