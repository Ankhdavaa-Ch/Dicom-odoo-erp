/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
class Dashboard extends Component {
    static template = "hdc_attendance_management.Dashboard";
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({month: "", cards: [], rows: [], section: "dashboard", selectedCard: null});
        onWillStart(() => this.load());
    }
    async load(month = null) {
        Object.assign(this.state, await this.orm.call("hdc.attendance.daily", "management_dashboard", [month]));
    }
    showCard(index) { this.state.selectedCard = index; }
    closeCard() { this.state.selectedCard = null; }
    get selectedCard() { return this.state.selectedCard === null ? null : this.state.cards[this.state.selectedCard]; }
    changeMonth(ev) { if (ev.target.value) return this.load(ev.target.value); }
    get reasonMax() { return Math.max(1, ...this.state.rows.map(r => this.reasons.reduce((sum, reason) => sum + (r[reason.key] || 0), 0))); }
    get workMax() { return Math.max(1, ...this.state.rows.map(r => Math.max(r.worked,r.planned))); }
    get reasons() { return [{key:"late",label:"Хоцорсон цаг",color:"#51bac6"},{key:"early",label:"Дутуу ажилласан цаг",color:"#f46f60"},{key:"outside",label:"Гадуур ажилласан цаг",color:"#4bc997"},{key:"overtime",label:"Илүү цаг",color:"#7caed6"},{key:"sick",label:"Өвчтэй цаг",color:"#9d8db6"},{key:"leave",label:"Чөлөөтэй цаг",color:"#ef9574"},{key:"annual",label:"Ээлжийн амралттай цаг",color:"#bcbcbc"},{key:"absent",label:"Тасалсан цаг",color:"#a56abe"}]; }
    get tabs() { return [{key:"dashboard",label:"Хяналтын самбар"},{key:"reference",label:"Лавлах"},{key:"plan",label:"Төлөвлөгөө"},{key:"register",label:"Бүртгэл"},{key:"balance",label:"Цагийн баланс"},{key:"settings",label:"Тохиргоо"},{key:"report",label:"Тайлан"},{key:"about",label:"Системийн тухай"}]; }
    selectTab(key) { this.state.section = key; }
    openAction(xmlid) { return this.action.doAction(xmlid); }
}
registry.category("actions").add("hdc_attendance_management.dashboard", Dashboard);
