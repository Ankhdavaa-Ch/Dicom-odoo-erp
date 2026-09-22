/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class HdcUnitDashboard extends Component {
    static template = "hdc_unit_management.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, data: null });
        onWillStart(async () => {
            this.state.data = await this.orm.call("hdc.employee.request", "get_unit_dashboard", []);
            this.state.loading = false;
        });
    }

    openRequests(ids, title) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: "hdc.employee.request",
            views: [[false, "list"], [false, "form"]],
            domain: [["id", "in", ids]],
            context: { create: false },
        });
    }

    openAnnualLeave() {
        return this.openRequests(this.state.data.annual_leave_request_ids, "Ээлжийн амралттай ажилтнууд");
    }

    openPending() {
        return this.openRequests(this.state.data.pending_request_ids, "Батлах хүсэлтүүд");
    }

    openAllRequests() {
        return this.openRequests(this.state.data.total_request_ids, "Нийт хүсэлтүүд");
    }

    openLate() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Хоцролттой ажилтнууд",
            res_model: "hdc.attendance.daily",
            views: [[false, "list"], [false, "form"]],
            domain: [["id", "in", this.state.data.late_attendance_ids]],
            context: { create: false },
        });
    }
}

registry.category("actions").add("hdc_unit_management.dashboard", HdcUnitDashboard);
