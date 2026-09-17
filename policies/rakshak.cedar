// Rakshak authorization policies.
//
// Enforced in src/common/authz.py, which mirrors these rules with Cedar
// semantics: default deny, and forbid overrides permit.
//
// Namespace PublicContent = EmergencyProtocols, AftermathSteps, FAQs, Resources.

// @id("permit_public_read")
// Anyone - including a bystander who installed the app 4 seconds ago and has
// no account - can read every piece of safety content. Read access is never
// gated on identity, because the identity check would cost seconds we do not
// have at a crash scene.
permit(
  principal,
  action in [Action::"read", Action::"search"],
  resource in Namespace::"PublicContent"
);

// @id("permit_admin_write")
// Only admins can change the content that people act on in an emergency.
permit(
  principal in Role::"admin",
  action in [Action::"write", Action::"delete"],
  resource in Namespace::"PublicContent"
);

// @id("forbid_non_admin_writes")
// Explicit forbid. Redundant against the default-deny, but it makes the intent
// auditable and produces a named reason in the denial rather than an empty one.
forbid(
  principal,
  action in [Action::"write", Action::"delete"],
  resource in Namespace::"PublicContent"
)
unless {
  principal in Role::"admin"
};
