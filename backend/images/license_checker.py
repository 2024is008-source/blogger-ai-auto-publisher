"""Asset-level license validation and attribution generator."""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.schemas import ImageAsset, LicenseFilter
from backend.utils.errors import InvalidLicenseError


@dataclass(frozen=True)
class LicensePolicy:
    canonical_name: str
    commercial_use: bool
    attribution_required: bool
    is_public_domain: bool
    default_url: str


KNOWN_LICENSES: dict[str, LicensePolicy] = {
    "cc0": LicensePolicy(
        canonical_name="CC0 1.0 Public Domain",
        commercial_use=True,
        attribution_required=False,
        is_public_domain=True,
        default_url="https://creativecommons.org/publicdomain/zero/1.0/",
    ),
    "pdm": LicensePolicy(
        canonical_name="Public Domain Mark 1.0",
        commercial_use=True,
        attribution_required=False,
        is_public_domain=True,
        default_url="https://creativecommons.org/publicdomain/mark/1.0/",
    ),
    "public domain": LicensePolicy(
        canonical_name="Public Domain",
        commercial_use=True,
        attribution_required=False,
        is_public_domain=True,
        default_url="https://creativecommons.org/publicdomain/mark/1.0/",
    ),
    "by": LicensePolicy(
        canonical_name="CC BY 4.0",
        commercial_use=True,
        attribution_required=True,
        is_public_domain=False,
        default_url="https://creativecommons.org/licenses/by/4.0/",
    ),
    "cc-by": LicensePolicy(
        canonical_name="CC BY 4.0",
        commercial_use=True,
        attribution_required=True,
        is_public_domain=False,
        default_url="https://creativecommons.org/licenses/by/4.0/",
    ),
    "by-sa": LicensePolicy(
        canonical_name="CC BY-SA 4.0",
        commercial_use=True,
        attribution_required=True,
        is_public_domain=False,
        default_url="https://creativecommons.org/licenses/by-sa/4.0/",
    ),
    "cc-by-sa": LicensePolicy(
        canonical_name="CC BY-SA 4.0",
        commercial_use=True,
        attribution_required=True,
        is_public_domain=False,
        default_url="https://creativecommons.org/licenses/by-sa/4.0/",
    ),
    "by-nc": LicensePolicy(
        canonical_name="CC BY-NC 4.0",
        commercial_use=False,
        attribution_required=True,
        is_public_domain=False,
        default_url="https://creativecommons.org/licenses/by-nc/4.0/",
    ),
    "by-nc-sa": LicensePolicy(
        canonical_name="CC BY-NC-SA 4.0",
        commercial_use=False,
        attribution_required=True,
        is_public_domain=False,
        default_url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
    ),
    "by-nd": LicensePolicy(
        canonical_name="CC BY-ND 4.0",
        commercial_use=True,
        attribution_required=True,
        is_public_domain=False,
        default_url="https://creativecommons.org/licenses/by-nd/4.0/",
    ),
    "pexels license": LicensePolicy(
        canonical_name="Pexels License",
        commercial_use=True,
        attribution_required=False,
        is_public_domain=False,
        default_url="https://www.pexels.com/license/",
    ),
    "pixabay license": LicensePolicy(
        canonical_name="Pixabay Content License",
        commercial_use=True,
        attribution_required=False,
        is_public_domain=False,
        default_url="https://pixabay.com/service/license-summary/",
    ),
}


def resolve_license_policy(raw_license_name: str) -> LicensePolicy | None:
    """Resolve an individual asset's license string to a verified LicensePolicy."""
    normalized = (raw_license_name or "").strip().lower()
    if not normalized:
        return None
    if normalized in KNOWN_LICENSES:
        return KNOWN_LICENSES[normalized]

    if "cc0" in normalized or "public domain" in normalized or normalized.startswith("pd"):
        return KNOWN_LICENSES["cc0"]
    if "pexels" in normalized:
        return KNOWN_LICENSES["pexels license"]
    if "pixabay" in normalized:
        return KNOWN_LICENSES["pixabay license"]
    if "nc" in normalized and "sa" in normalized:
        return KNOWN_LICENSES["by-nc-sa"]
    if "nc" in normalized:
        return KNOWN_LICENSES["by-nc"]
    if "nd" in normalized:
        return KNOWN_LICENSES["by-nd"]
    if "by-sa" in normalized or "by sa" in normalized:
        return KNOWN_LICENSES["by-sa"]
    if "cc by" in normalized or "cc-by" in normalized or normalized == "by":
        return KNOWN_LICENSES["by"]
    return None


def build_attribution_text(asset: ImageAsset) -> str:
    """Build compliant attribution text for an image asset."""
    creator = asset.creator_name or "Unknown creator"
    title = asset.title or "Image"
    if not asset.attribution_required:
        return f"Photo: {title} by {creator} ({asset.source_provider}, {asset.license_name})"
    return (
        f'"{title}" by {creator} via {asset.source_provider}, '
        f"licensed under {asset.license_name} ({asset.license_url})"
    )


def validate_and_enrich_asset(asset: ImageAsset, license_filter: LicenseFilter) -> ImageAsset:
    """Validate an individual image's license against the requested filter.

    Raises InvalidLicenseError if the license is missing, unrecognized, or incompatible.
    """
    policy = resolve_license_policy(asset.license_name)
    if policy is None:
        raise InvalidLicenseError(
            f"Asset '{asset.id}' from {asset.source_provider} has unclear or unsupported license '{asset.license_name}'."
        )

    asset.license_name = policy.canonical_name
    asset.license_url = asset.license_url or policy.default_url
    asset.commercial_use_permitted = policy.commercial_use
    asset.attribution_required = policy.attribution_required
    asset.attribution_text = build_attribution_text(asset)

    if license_filter == LicenseFilter.CC0_PUBLIC_DOMAIN and not policy.is_public_domain:
        raise InvalidLicenseError(
            f"Asset '{asset.id}' license '{policy.canonical_name}' is not CC0/Public Domain."
        )
    if license_filter == LicenseFilter.COMMERCIAL_PERMITTED and not policy.commercial_use:
        raise InvalidLicenseError(
            f"Asset '{asset.id}' license '{policy.canonical_name}' does not permit commercial use."
        )
    if license_filter == LicenseFilter.CC_WITH_ATTRIBUTION and not (
        policy.canonical_name.startswith("CC ") or policy.is_public_domain
    ):
        raise InvalidLicenseError(
            f"Asset '{asset.id}' license '{policy.canonical_name}' is not a Creative Commons / Public Domain license."
        )
    return asset
