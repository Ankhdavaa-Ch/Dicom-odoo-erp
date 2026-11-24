/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
class Dashboard extends Component {
    static template = "hdc_attendance_management.Dashboard";
    setup() {
        this.orm = useService("orm");
        this.state = useState({month: "", cards: [], rows: []});
        onWillStart(() => this.load());
    }
    async load(month = null) {
        Object.assign(this.state, await this.orm.call("hdc.attendance.daily", "management_dashboard", [month]));
    }
    changeMonth(ev) { if (ev.target.value) return this.load(ev.target.value); }
    get maxHours() { return Math.max(1, ...this.state.rows.map(r => r.worked), ...this.state.rows.map(r => r.late+r.early+r.overtime)); }
}
registry.category("actions").add("hdc_attendance_management.dashboard", Dashboard);
