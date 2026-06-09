from app.models.policy import TenantPolicy
from app.models.schemas import CheckPasswordRequest, CheckPasswordResponse, PasswordStatus


def evaluate_policy(
    request: CheckPasswordRequest,
    policy: TenantPolicy,
    breached: bool,
) -> CheckPasswordResponse:
    failed_rules: list[str] = []

    if breached:
        return CheckPasswordResponse(
            status=PasswordStatus.BREACHED,
            score=request.zxcvbn_score,
            failed_rules=["hibp_breached"],
            suggestion="This password has appeared in data breaches. Use a completely new password.",
        )

    if request.password_length < policy.min_length:
        failed_rules.append("min_length")
    if request.password_length > policy.max_length:
        failed_rules.append("max_length")
    if policy.require_uppercase and not request.has_uppercase:
        failed_rules.append("require_uppercase")
    if policy.require_lowercase and not request.has_lowercase:
        failed_rules.append("require_lowercase")
    if policy.require_digit and not request.has_digit:
        failed_rules.append("require_digit")
    if policy.require_symbol and not request.has_symbol:
        failed_rules.append("require_symbol")
    if request.zxcvbn_score < policy.zxcvbn_min:
        failed_rules.append("zxcvbn_min")

    if failed_rules:
        return CheckPasswordResponse(
            status=PasswordStatus.RISKY,
            score=request.zxcvbn_score,
            failed_rules=failed_rules,
            suggestion="Add more length, variety, and uncommon wording to strengthen the password.",
        )

    return CheckPasswordResponse(
        status=PasswordStatus.SAFE,
        score=request.zxcvbn_score,
        failed_rules=[],
        suggestion="Password meets current policy.",
    )
