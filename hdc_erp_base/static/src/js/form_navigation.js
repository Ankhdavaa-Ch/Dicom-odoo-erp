/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(FormController.prototype, {
    async hdcBack() {
        if (this.env.inDialog) {
            return;
        }
        const record = this.model.root;
        const dirty = await record.isDirty();
        if (!dirty && !record.isNew) {
            this.env.config.historyBack();
            return;
        }

        this.dialogService.add(ConfirmationDialog, {
            title: "Хадгалаагүй өөрчлөлт",
            body: "Өөрчлөлтөө хадгалах уу? Хадгалахгүй буцах бол «Хадгалахгүй» товчийг дарна уу.",
            confirmLabel: "Хадгалаад буцах",
            cancelLabel: "Хадгалахгүй",
            confirm: async () => {
                const saved = await this.saveButtonClicked();
                if (saved) {
                    this.env.config.historyBack();
                }
            },
            cancel: async () => {
                const wasNew = record.isNew;
                await this.discard();
                if (!wasNew) {
                    this.env.config.historyBack();
                }
            },
        });
    },
});
