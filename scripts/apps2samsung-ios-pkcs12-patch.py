#!/usr/bin/env python3
"""Rebuild Apps2Samsung with an iOS-only PKCS#12 import correction.

Pinned inputs: Apps2Samsung v3.0.0-beta and PatrickSt1991/tizen-sdb eb254cea.
No certificate material, Apple credentials, or TV access are used.
"""
from pathlib import Path

src = Path("tizen-sdb/src/TizenSdb.Core/SigningManager/TizenWgtSigner.cs")
code = src.read_text(encoding="utf-8")
old = """            var importFlags = (IsMobileHost || RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                ? X509KeyStorageFlags.Exportable
                : X509KeyStorageFlags.DefaultKeySet;"""
new = """            var importFlags = (OperatingSystem.IsIOS() || OperatingSystem.IsMacCatalyst() || OperatingSystem.IsTvOS())
                ? X509KeyStorageFlags.EphemeralKeySet
                : (IsMobileHost || RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                    ? X509KeyStorageFlags.Exportable
                    : X509KeyStorageFlags.DefaultKeySet;"""
if code.count(old) != 1:
    raise SystemExit("PATCH_FAIL: expected one collection-import flags block")
code = code.replace(old, new, 1)

old = """            if (IsMobileHost)
            {
                // Android (MonoVM) and iOS/Mac Catalyst: load in-memory only."""
new = """            if (OperatingSystem.IsIOS() || OperatingSystem.IsMacCatalyst() || OperatingSystem.IsTvOS())
            {
                // Apple mobile platforms reject Exportable for PKCS#12.
                return new X509Certificate2(
                    pfxPath, password, X509KeyStorageFlags.EphemeralKeySet);
            }
            if (IsMobileHost)
            {
                // Android (MonoVM): keep its existing ephemeral/exportable path."""
if code.count(old) != 1:
    raise SystemExit("PATCH_FAIL: expected one mobile leaf-certificate block")
code = code.replace(old, new, 1)
src.write_text(code, encoding="utf-8")

project = Path("apps2samsung/Apps2Samsung.Core/Apps2Samsung.Core.csproj")
original = project.read_text(encoding="utf-8")
old = 'PackageReference Include="TizenSdb.Core" Version="1.1.7"'
new = 'PackageReference Include="TizenSdb.Core" Version="1.1.7-iosfix.20261025"'
if original.count(old) != 1:
    raise SystemExit("PATCH_FAIL: expected the pinned library version")
project.write_text(original.replace(old, new, 1), encoding="utf-8")

cfg = Path("apps2samsung/NuGet.Config")
if cfg.exists():
    raise SystemExit("PATCH_FAIL: refuse to overwrite an upstream NuGet.Config")
cfg.write_text("""<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="ios-fixed-local" value="./local-nuget" />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
  </packageSources>
</configuration>
""", encoding="utf-8")
print("IOS_PKCS12_LEAF=PATCHED; IOS_PKCS12_CHAIN=PATCHED")
print("ANDROID_WINDOWS_IMPORT_BEHAVIOR=UNCHANGED")
