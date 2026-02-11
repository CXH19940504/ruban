from ruban.utils.alert import AlertTrigger


class TestRuleTrigger:

    def test_load(self):
        # 1. 加载告警规则
        rules = AlertTrigger().alert_rules
        assert len(rules) == 2

    def test_rule1(self):
        # 2. 测试场景1：quantity从0增加（触发rule_1）
        print("\n=== 测试场景1：库存从0新增 ===")
        old_data1 = {"last_quantity": 0, "status": 0}
        new_data1 = {"last_quantity": 500, "status": 0}
        alert = AlertTrigger().check_alerts(old_data1, new_data1)
        assert alert is None
        new_data3 = {"last_quantity": 500, "status": 3}
        alert = AlertTrigger().check_alerts(old_data1, new_data3)
        print(f"触发告警：{alert.name} | 描述：{alert.description}")
        assert alert.rule_id == 'rule_1'

    def test_rule2(self):
        # 3. 测试场景2：status从0变为3（触发rule_2）
        print("\n=== 测试场景2：订单状态变为3 ===")
        old_data2 = {"last_quantity": 0, "status": 0}
        new_data2 = {"last_quantity": 0, "status": 3}
        alert = AlertTrigger().check_alerts(old_data2, new_data2)
        print(f"触发告警：{alert.name} | 描述：{alert.description}")
        assert alert.rule_id == 'rule_2'

    def test_not_trigger(self):
        # 4. 测试场景3：status从0变为5（不触发任何规则）
        print("\n=== 测试场景3：订单状态变为5（无告警） ===")
        old_data3 = {"last_quantity": 0, "status": 0}
        new_data3 = {"last_quantity": 0, "status": 5}
        alert = AlertTrigger().check_alerts(old_data3, new_data3)
        assert alert is None

    def test_is_triggered(self):
        assert False
