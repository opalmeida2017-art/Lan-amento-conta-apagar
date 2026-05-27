class ImportaXMLController:
    def __init__(self, app_controller):
        self.app_controller = app_controller
        self.view = None

    def iniciar_importacao(self, itens_xml):
        self.app_controller.solicitar_importacao_xml(itens_xml)
