from ._shared import *  # noqa: F401,F403


class TeacherOrganizationRbacPolicyToolingTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="org_teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.org_a = Organization.objects.create(name="Org Alpha")
        self.org_b = Organization.objects.create(name="Org Beta")
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.staff,
            role=OrganizationMembership.ROLE_TEACHER,
        )
        self.class_a = Class.objects.create(name="Alpha Cohort", join_code="ORGA1234", organization=self.org_a)
        self.class_b = Class.objects.create(name="Beta Cohort", join_code="ORGB1234", organization=self.org_b)
        _force_login_staff_verified(self.client, self.staff)

    def _promote_staff_to_superuser(self):
        self.staff.is_superuser = True
        self.staff.save(update_fields=["is_superuser"])

    def test_org_admin_can_upsert_scoped_grant_from_teach_home(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_target_org",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )

        resp = self.client.post(
            "/teach/rbac/module-scope-grant/upsert",
            {
                "rbac_class_id": str(self.class_a.id),
                "rbac_user_id": str(target_staff.id),
                "rbac_capability": ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
                "rbac_effect": ClassStaffModuleScopeGrant.EFFECT_DENY,
                "rbac_module_start": "0",
                "rbac_module_end": "1",
                "rbac_grant_active": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        grant = ClassStaffModuleScopeGrant.objects.filter(
            classroom=self.class_a,
            user=target_staff,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
            effect=ClassStaffModuleScopeGrant.EFFECT_DENY,
            module_order_start=0,
            module_order_end=1,
        ).first()
        self.assertIsNotNone(grant)
        self.assertTrue(grant.is_active)

        event = AuditEvent.objects.filter(action="rbac.scope_grant.portal_upsert", target_id=str(grant.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_org_admin_can_toggle_scoped_grant_active_from_teach_home(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_toggle_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        grant = ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=target_staff,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_DELETE,
            effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        resp = self.client.post(
            "/teach/rbac/module-scope-grant/set-active",
            {"rbac_grant_id": str(grant.id), "rbac_grant_active": "0"},
        )
        self.assertEqual(resp.status_code, 302)
        grant.refresh_from_db()
        self.assertFalse(grant.is_active)
        event = AuditEvent.objects.filter(action="rbac.scope_grant.portal_set_active", target_id=str(grant.id)).first()
        self.assertIsNotNone(event)

    def test_org_admin_can_simulate_rbac_from_teach_home(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_sim_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        module = Module.objects.create(classroom=self.class_a, title="Sim Module", order_index=0)

        resp = self.client.post(
            "/teach/rbac/simulate",
            {
                "rbac_sim_user_id": str(target_staff.id),
                "rbac_sim_capability": ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
                "rbac_sim_class_id": str(self.class_a.id),
                "rbac_sim_module_id": str(module.id),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("rbac_sim_result=1", resp["Location"])

        result_page = self.client.get(resp["Location"])
        self.assertEqual(result_page.status_code, 200)
        self.assertContains(result_page, "Simulation result")
        self.assertContains(result_page, "reason=")

        event = AuditEvent.objects.filter(action="rbac.simulate.portal", target_id=str(target_staff.id)).first()
        self.assertIsNotNone(event)

    def test_org_admin_bulk_simulation_matrix_scopes_to_class_org(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])

        alpha_staff = get_user_model().objects.create_user(
            username="rbac_bulk_alpha",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        beta_staff = get_user_model().objects.create_user(
            username="rbac_bulk_beta",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=alpha_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=beta_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )

        resp = self.client.get(
            "/teach",
            {
                "portal_mode": "policy",
                "advanced": "1",
                "rbac_tools": "1",
                "rbac_bulk_class_id": str(self.class_a.id),
                "rbac_bulk_capability": OrganizationRoleCapability.CAP_CLASS_VIEW,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bulk simulation result")
        self.assertContains(resp, "class=Alpha Cohort")
        self.assertContains(resp, alpha_staff.username)
        self.assertContains(resp, beta_staff.username)
        self.assertContains(resp, "no_membership_for_class_org")

    def test_org_admin_can_filter_rbac_audit_ops_feed(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])

        AuditEvent.objects.create(
            actor_user=self.staff,
            classroom=self.class_a,
            action="rbac.scope_grant.portal_upsert",
            target_type="ClassStaffModuleScopeGrant",
            target_id="alpha-1",
            summary="audit keep alpha",
            metadata={"organization_id": self.org_a.id},
        )
        AuditEvent.objects.create(
            actor_user=self.staff,
            classroom=self.class_b,
            action="rbac.scope_grant.portal_upsert",
            target_type="ClassStaffModuleScopeGrant",
            target_id="beta-1",
            summary="audit drop beta class",
            metadata={"organization_id": self.org_b.id},
        )
        AuditEvent.objects.create(
            actor_user=self.staff,
            classroom=self.class_a,
            action="organization.membership.upsert",
            target_type="OrganizationMembership",
            target_id="alpha-2",
            summary="audit drop action family",
            metadata={"organization_id": self.org_a.id},
        )

        resp = self.client.get(
            "/teach",
            {
                "portal_mode": "policy",
                "advanced": "1",
                "rbac_tools": "1",
                "rbac_audit_action": "rbac.scope_grant.",
                "rbac_audit_class_id": str(self.class_a.id),
                "rbac_audit_limit": "25",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "RBAC audit operations")
        self.assertContains(resp, "audit keep alpha")
        self.assertNotContains(resp, "audit drop beta class")
        self.assertNotContains(resp, "audit drop action family")

    def test_org_admin_rbac_query_param_does_not_enable_bulk_simulation_ui(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])

        resp = self.client.get(
            "/teach",
            {
                "rbac_tools": "1",
                "rbac_bulk_class_id": str(self.class_a.id),
                "rbac_bulk_capability": ClassStaffModuleScopeGrant.CAP_SUBMISSION_DELETE,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "RBAC tools")
        self.assertNotContains(resp, "Bulk simulation result")

    def test_org_admin_rbac_query_param_does_not_enable_audit_feed_ui(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])

        resp = self.client.get(
            "/teach",
            {
                "rbac_tools": "1",
                "rbac_audit_action": "rbac.scope_grant.",
                "rbac_audit_class_id": str(self.class_a.id),
                "rbac_audit_limit": "25",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "RBAC tools")
        self.assertNotContains(resp, "RBAC audit operations")

    def test_org_admin_can_export_rbac_policy_json(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_policy_export_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        OrganizationRoleCapability.objects.create(
            organization=self.org_a,
            role=OrganizationMembership.ROLE_TEACHER,
            capability=OrganizationRoleCapability.CAP_POLICY_MANAGE,
            is_active=True,
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=target_staff,
            capability=ClassStaffModuleScopeGrant.CAP_POLICY_MANAGE,
            effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        resp = self.client.get("/teach/rbac/policy/export")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/json", resp["Content-Type"])
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(payload.get("schema_version"), "classhub.rbac_policy.v1")
        self.assertTrue(any(org.get("name") == self.org_a.name for org in payload.get("organizations", [])))
        self.assertTrue(
            any(grant.get("class_join_code") == self.class_a.join_code for grant in payload.get("scoped_grants", []))
        )
        event = AuditEvent.objects.filter(action="rbac.policy.export").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_org_admin_can_import_rbac_policy_json(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_policy_import_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        policy = {
            "schema_version": "classhub.rbac_policy.v1",
            "organizations": [
                {
                    "name": self.org_a.name,
                    "role_capabilities": [
                        {
                            "role": OrganizationMembership.ROLE_VIEWER,
                            "capability": OrganizationRoleCapability.CAP_CLASS_VIEW,
                            "is_active": True,
                        }
                    ],
                }
            ],
            "scoped_grants": [
                {
                    "class_join_code": self.class_a.join_code,
                    "username": target_staff.username,
                    "capability": ClassStaffModuleScopeGrant.CAP_POLICY_MANAGE,
                    "effect": ClassStaffModuleScopeGrant.EFFECT_ALLOW,
                    "module_order_start": 0,
                    "module_order_end": 0,
                    "is_active": True,
                }
            ],
        }

        resp = self.client.post(
            "/teach/rbac/policy/import",
            {
                "rbac_policy_file": SimpleUploadedFile(
                    "rbac_policy.json",
                    json.dumps(policy).encode("utf-8"),
                    content_type="application/json",
                )
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.assertTrue(
            OrganizationRoleCapability.objects.filter(
                organization=self.org_a,
                role=OrganizationMembership.ROLE_VIEWER,
                capability=OrganizationRoleCapability.CAP_CLASS_VIEW,
                is_active=True,
            ).exists()
        )
        self.assertTrue(
            ClassStaffModuleScopeGrant.objects.filter(
                classroom=self.class_a,
                user=target_staff,
                capability=ClassStaffModuleScopeGrant.CAP_POLICY_MANAGE,
                effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
                module_order_start=0,
                module_order_end=0,
                is_active=True,
            ).exists()
        )
        event = AuditEvent.objects.filter(action="rbac.policy.import").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_org_admin_policy_export_includes_custom_roles_and_assignments(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_custom_export_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        role = OrganizationCustomRole.objects.create(
            organization=self.org_a,
            slug="district_exporter",
            name="District Exporter",
            description="Can export curriculum policy bundles",
            is_active=True,
        )
        OrganizationCustomRoleCapability.objects.create(
            role=role,
            capability=OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
            is_active=True,
        )
        OrganizationCustomRoleAssignment.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=role,
            is_active=True,
        )

        resp = self.client.get("/teach/rbac/policy/export")
        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(any(row.get("slug") == "district_exporter" for row in payload.get("custom_roles", [])))
        self.assertTrue(
            any(
                row.get("username") == target_staff.username and row.get("role_slug") == "district_exporter"
                for row in payload.get("custom_role_assignments", [])
            )
        )

    def test_org_admin_policy_import_can_upsert_custom_roles_and_assignments(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_custom_import_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        policy = {
            "schema_version": "classhub.rbac_policy.v1",
            "organizations": [],
            "scoped_grants": [],
            "custom_roles": [
                {
                    "organization_name": self.org_a.name,
                    "slug": "ops_observer",
                    "name": "Ops Observer",
                    "description": "Read-only operations observer",
                    "is_active": True,
                    "capabilities": [
                        {"capability": OrganizationRoleCapability.CAP_CLASS_VIEW, "is_active": True},
                    ],
                }
            ],
            "custom_role_assignments": [
                {
                    "organization_name": self.org_a.name,
                    "role_slug": "ops_observer",
                    "username": target_staff.username,
                    "is_active": True,
                }
            ],
        }

        resp = self.client.post(
            "/teach/rbac/policy/import",
            {
                "rbac_policy_file": SimpleUploadedFile(
                    "rbac_policy.json",
                    json.dumps(policy).encode("utf-8"),
                    content_type="application/json",
                )
            },
        )
        self.assertEqual(resp.status_code, 302)
        role = OrganizationCustomRole.objects.filter(organization=self.org_a, slug="ops_observer").first()
        self.assertIsNotNone(role)
        self.assertTrue(
            OrganizationCustomRoleCapability.objects.filter(
                role=role,
                capability=OrganizationRoleCapability.CAP_CLASS_VIEW,
                is_active=True,
            ).exists()
        )
        self.assertTrue(
            OrganizationCustomRoleAssignment.objects.filter(
                organization=self.org_a,
                role=role,
                user=target_staff,
                is_active=True,
            ).exists()
        )

    def test_org_admin_can_upsert_custom_roles_from_teach_home(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_custom_assign_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )

        role_resp = self.client.post(
            "/teach/rbac/custom-role/upsert",
            {
                "rbac_custom_role_org_id": str(self.org_a.id),
                "rbac_custom_role_slug": "district_exporter",
                "rbac_custom_role_name": "District Exporter",
                "rbac_custom_role_description": "District export rights",
                "rbac_custom_role_active": "1",
            },
        )
        self.assertEqual(role_resp.status_code, 302)
        role = OrganizationCustomRole.objects.filter(organization=self.org_a, slug="district_exporter").first()
        self.assertIsNotNone(role)

        cap_resp = self.client.post(
            "/teach/rbac/custom-role/capability/upsert",
            {
                "rbac_custom_role_cap_org_id": str(self.org_a.id),
                "rbac_custom_role_cap_slug": "district_exporter",
                "rbac_custom_role_capability": OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
                "rbac_custom_role_cap_active": "1",
            },
        )
        self.assertEqual(cap_resp.status_code, 302)
        self.assertTrue(
            OrganizationCustomRoleCapability.objects.filter(
                role=role,
                capability=OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
                is_active=True,
            ).exists()
        )

        assign_resp = self.client.post(
            "/teach/rbac/custom-role/assignment/upsert",
            {
                "rbac_custom_role_assign_org_id": str(self.org_a.id),
                "rbac_custom_role_assign_slug": "district_exporter",
                "rbac_custom_role_assign_user_id": str(target_staff.id),
                "rbac_custom_role_assign_active": "1",
            },
        )
        self.assertEqual(assign_resp.status_code, 302)
        self.assertTrue(
            OrganizationCustomRoleAssignment.objects.filter(
                organization=self.org_a,
                role=role,
                user=target_staff,
                is_active=True,
            ).exists()
        )
        self.assertTrue(AuditEvent.objects.filter(action="organization.custom_role.portal_upsert").exists())
        self.assertTrue(AuditEvent.objects.filter(action="organization.custom_role_capability.portal_upsert").exists())
        self.assertTrue(AuditEvent.objects.filter(action="organization.custom_role_assignment.portal_upsert").exists())

    @override_settings(CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=True)

    def test_policy_approval_workflow_requires_separate_reviewer(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])

        request_resp = self.client.post(
            "/teach/rbac/custom-role/upsert",
            {
                "rbac_custom_role_org_id": str(self.org_a.id),
                "rbac_custom_role_slug": "review_gated_role",
                "rbac_custom_role_name": "Review Gated Role",
                "rbac_custom_role_description": "Requires approval",
                "rbac_custom_role_active": "1",
            },
        )
        self.assertEqual(request_resp.status_code, 302)
        change = RbacPolicyChangeRequest.objects.filter(
            request_type=RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_UPSERT
        ).first()
        self.assertIsNotNone(change)
        self.assertEqual(change.status, RbacPolicyChangeRequest.STATUS_PENDING)
        self.assertFalse(OrganizationCustomRole.objects.filter(organization=self.org_a, slug="review_gated_role").exists())

        self_review_resp = self.client.post(
            "/teach/rbac/change-request/review",
            {
                "rbac_change_review_id": str(change.id),
                "rbac_change_review_decision": "approve",
            },
        )
        self.assertEqual(self_review_resp.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.status, RbacPolicyChangeRequest.STATUS_PENDING)

        reviewer = get_user_model().objects.create_user(
            username="rbac_change_reviewer",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=reviewer,
            role=OrganizationMembership.ROLE_ADMIN,
            is_active=True,
        )
        _force_login_staff_verified(self.client, reviewer)
        approve_resp = self.client.post(
            "/teach/rbac/change-request/review",
            {
                "rbac_change_review_id": str(change.id),
                "rbac_change_review_decision": "approve",
                "rbac_change_review_note": "Looks good.",
            },
        )
        self.assertEqual(approve_resp.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.status, RbacPolicyChangeRequest.STATUS_APPROVED)
        self.assertEqual(change.reviewed_by_id, reviewer.id)
        self.assertTrue(OrganizationCustomRole.objects.filter(organization=self.org_a, slug="review_gated_role").exists())

    @override_settings(CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=True)

    def test_policy_import_is_queued_and_applied_after_approval(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_policy_queue_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        policy = {
            "schema_version": "classhub.rbac_policy.v1",
            "organizations": [],
            "scoped_grants": [],
            "custom_roles": [
                {
                    "organization_name": self.org_a.name,
                    "slug": "queued_policy_role",
                    "name": "Queued Policy Role",
                    "description": "Policy import via approval",
                    "is_active": True,
                    "capabilities": [
                        {"capability": OrganizationRoleCapability.CAP_CLASS_VIEW, "is_active": True},
                    ],
                }
            ],
            "custom_role_assignments": [
                {
                    "organization_name": self.org_a.name,
                    "role_slug": "queued_policy_role",
                    "username": target_staff.username,
                    "is_active": True,
                }
            ],
        }

        queue_resp = self.client.post(
            "/teach/rbac/policy/import",
            {
                "rbac_policy_file": SimpleUploadedFile(
                    "rbac_policy.json",
                    json.dumps(policy).encode("utf-8"),
                    content_type="application/json",
                )
            },
        )
        self.assertEqual(queue_resp.status_code, 302)
        request_row = RbacPolicyChangeRequest.objects.filter(
            request_type=RbacPolicyChangeRequest.REQUEST_POLICY_IMPORT
        ).first()
        self.assertIsNotNone(request_row)
        self.assertEqual(request_row.status, RbacPolicyChangeRequest.STATUS_PENDING)
        self.assertFalse(OrganizationCustomRole.objects.filter(organization=self.org_a, slug="queued_policy_role").exists())

        reviewer = get_user_model().objects.create_user(
            username="rbac_policy_queue_reviewer",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=reviewer,
            role=OrganizationMembership.ROLE_ADMIN,
            is_active=True,
        )
        _force_login_staff_verified(self.client, reviewer)
        approve_resp = self.client.post(
            "/teach/rbac/change-request/review",
            {
                "rbac_change_review_id": str(request_row.id),
                "rbac_change_review_decision": "approve",
            },
        )
        self.assertEqual(approve_resp.status_code, 302)
        request_row.refresh_from_db()
        self.assertEqual(request_row.status, RbacPolicyChangeRequest.STATUS_APPROVED)
        self.assertTrue(OrganizationCustomRole.objects.filter(organization=self.org_a, slug="queued_policy_role").exists())

    @override_settings(CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=True)

    def test_teacher_with_export_capability_cannot_review_policy_change_request(self):
        self._promote_staff_to_superuser()
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])

        request_resp = self.client.post(
            "/teach/rbac/custom-role/upsert",
            {
                "rbac_custom_role_org_id": str(self.org_a.id),
                "rbac_custom_role_slug": "restricted_review_target",
                "rbac_custom_role_name": "Restricted Review Target",
                "rbac_custom_role_description": "Queued for review",
                "rbac_custom_role_active": "1",
            },
        )
        self.assertEqual(request_resp.status_code, 302)
        change = RbacPolicyChangeRequest.objects.filter(
            request_type=RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_UPSERT
        ).first()
        self.assertIsNotNone(change)
        self.assertEqual(change.status, RbacPolicyChangeRequest.STATUS_PENDING)

        reviewer = get_user_model().objects.create_user(
            username="rbac_export_only_reviewer",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=reviewer,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        export_only_role = OrganizationCustomRole.objects.create(
            organization=self.org_a,
            slug="review_export_only",
            name="Review Export Only",
            description="Can export but cannot review approvals",
            is_active=True,
        )
        OrganizationCustomRoleCapability.objects.create(
            role=export_only_role,
            capability=OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
            is_active=True,
        )
        OrganizationCustomRoleAssignment.objects.create(
            organization=self.org_a,
            role=export_only_role,
            user=reviewer,
            is_active=True,
        )

        _force_login_staff_verified(self.client, reviewer)
        review_resp = self.client.post(
            "/teach/rbac/change-request/review",
            {
                "rbac_change_review_id": str(change.id),
                "rbac_change_review_decision": "approve",
            },
        )
        self.assertEqual(review_resp.status_code, 302)
        self.assertIn("superuser", review_resp["Location"].lower())
        change.refresh_from_db()
        self.assertEqual(change.status, RbacPolicyChangeRequest.STATUS_PENDING)
        self.assertIsNone(change.reviewed_by_id)
        self.assertFalse(
            OrganizationCustomRole.objects.filter(organization=self.org_a, slug="restricted_review_target").exists()
        )

    def test_teacher_role_cannot_import_or_export_rbac_policy(self):
        export_resp = self.client.get("/teach/rbac/policy/export")
        self.assertEqual(export_resp.status_code, 302)
        self.assertIn("/teach?error=", export_resp["Location"])

        import_resp = self.client.post(
            "/teach/rbac/policy/import",
            {
                "rbac_policy_file": SimpleUploadedFile(
                    "rbac_policy.json",
                    b'{"schema_version":"classhub.rbac_policy.v1","organizations":[],"scoped_grants":[]}',
                    content_type="application/json",
                )
            },
        )
        self.assertEqual(import_resp.status_code, 302)
        self.assertIn("/teach?error=", import_resp["Location"])
        self.assertFalse(AuditEvent.objects.filter(action="rbac.policy.import").exists())

    def test_teacher_role_cannot_upsert_scoped_grant_from_teach_home(self):
        target_staff = get_user_model().objects.create_user(
            username="rbac_blocked_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )

        resp = self.client.post(
            "/teach/rbac/module-scope-grant/upsert",
            {
                "rbac_class_id": str(self.class_a.id),
                "rbac_user_id": str(target_staff.id),
                "rbac_capability": ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
                "rbac_effect": ClassStaffModuleScopeGrant.EFFECT_ALLOW,
                "rbac_module_start": "0",
                "rbac_module_end": "0",
                "rbac_grant_active": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertFalse(
            ClassStaffModuleScopeGrant.objects.filter(
                classroom=self.class_a,
                user=target_staff,
                capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
                effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
                module_order_start=0,
                module_order_end=0,
            ).exists()
        )

    def test_scoped_submission_view_grant_limits_material_submissions_route(self):
        module_1 = Module.objects.create(classroom=self.class_a, title="Session 1", order_index=0)
        module_2 = Module.objects.create(classroom=self.class_a, title="Session 2", order_index=1)
        material_1 = Material.objects.create(
            module=module_1,
            title="Upload 1",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        material_2 = Material.objects.create(
            module=module_2,
            title="Upload 2",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=self.class_a, display_name="Ada")
        submission_1 = Submission.objects.create(
            material=material_1,
            student=student,
            original_filename="one.sb3",
            file=SimpleUploadedFile("one.sb3", _sample_sb3_bytes()),
        )
        submission_2 = Submission.objects.create(
            material=material_2,
            student=student,
            original_filename="two.sb3",
            file=SimpleUploadedFile("two.sb3", _sample_sb3_bytes()),
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=self.staff,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        allowed = self.client.get(f"/teach/material/{material_1.id}/submissions")
        self.assertEqual(allowed.status_code, 200)
        blocked = self.client.get(f"/teach/material/{material_2.id}/submissions")
        self.assertEqual(blocked.status_code, 404)

        allowed_download = self.client.get(f"/submission/{submission_1.id}/download")
        self.assertEqual(allowed_download.status_code, 200)
        blocked_download = self.client.get(f"/submission/{submission_2.id}/download")
        self.assertEqual(blocked_download.status_code, 403)

    @override_settings(CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=True)

    def test_scoped_submission_delete_grant_limits_gallery_moderation(self):
        module_1 = Module.objects.create(classroom=self.class_a, title="Session 1", order_index=0)
        module_2 = Module.objects.create(classroom=self.class_a, title="Session 2", order_index=1)
        gallery_1 = Material.objects.create(
            module=module_1,
            title="Gallery 1",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        gallery_2 = Material.objects.create(
            module=module_2,
            title="Gallery 2",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=self.class_a, display_name="Ada")
        submission_1 = Submission.objects.create(
            material=gallery_1,
            student=student,
            original_filename="one.sb3",
            file=SimpleUploadedFile("one.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=False,
        )
        submission_2 = Submission.objects.create(
            material=gallery_2,
            student=student,
            original_filename="two.sb3",
            file=SimpleUploadedFile("two.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=False,
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=self.staff,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_DELETE,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        allowed = self.client.post(
            f"/teach/material/{gallery_1.id}/submission/{submission_1.id}/moderate",
            {"approve": "1"},
        )
        self.assertEqual(allowed.status_code, 302)
        blocked = self.client.post(
            f"/teach/material/{gallery_2.id}/submission/{submission_2.id}/moderate",
            {"approve": "1"},
        )
        self.assertEqual(blocked.status_code, 403)

