import importlib
import os
from pathlib import Path
from lsassy.logger import lsassy_logger


class Writer:
    """
    Class used to write output results either on screen and/or in a file
    """
    def __init__(self, credentials, tickets, masterkeys):
        self._credentials = credentials
        self._tickets = tickets
        self._masterkeys = masterkeys
        

    def get_output(self, out_format, users_only=False, tickets=False, masterkeys=False):
        """
        Get credentials output in given format
        :param out_format: Format from output package
        :param users_only: If set, only returns users account, else returns users and computers accounts
        :return: Output string
        """
        try:
            output_method = importlib.import_module("lsassy.output.{}_output".format(out_format.lower()), "Output").Output(self._credentials, users_only, tickets, masterkeys)
        except ModuleNotFoundError:
            lsassy_logger.error("Output module '{}' doesn't exist".format(out_format.lower()), exc_info=True)
            return None

        return output_method.get_output()

    def write(self, file_format, out_format="pretty", output_file=None, quiet=False, users_only=False, tickets=False, masterkeys=False, kerberos_dir=None, masterkeys_file=None):

        """
        Displays content to stdout and/or a file
        :param out_format: Output format
        :param output_file: Output file
        :param file_format: File Logs Format
        :param quiet: If set, doesn't display on stdout
        :param users_only: If set, only returns users account, else returns users and computers accounts
        :param kerberos_dir: If set, saves Kerberos ticket to specified directory
        :param masterkeys_file: If set, saves DPAPI masterkeys to specified directory
        :return: Success status
        """
        output = self.get_output(out_format, users_only, tickets, masterkeys)
        
        if file_format is None:
            file_content = output
        else:
            file_content = self.get_output(file_format, users_only, tickets, masterkeys)

        if output is None:
            lsassy_logger.error("An error occurred while writing credentials", exc_info=True)
            return None

        if not quiet:
            for line in output.split("\n"):
                print(line)

        if output_file is not None:
            path = Path(output_file).parent
            if not os.path.isdir(path):
                lsassy_logger.error("Directory {} does not exist".format(path))
                return None

            with open(output_file, 'a+') as f:
                f.write(file_content + "\n")
            print("Credentials saved to {}".format(output_file))

        if os.name == 'nt':
            output_dir = '%LocalAppData%\\lsassy'
        else:
            output_dir = os.path.expanduser('~') + '/.config/lsassy'

        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                self.write_tickets(kerberos_dir, quiet)
                self.write_masterkeys(masterkeys_file, quiet)
            except Exception:
                return output
        else:
            self.write_tickets(kerberos_dir, quiet)
            self.write_masterkeys(masterkeys_file, quiet)
        return output

    def write_tickets(self, kerberos_dir=None, quiet=False):
        """
        Output masterkeys to file
        :param kerberos_dir: Output dir
        :param quiet: If set, doesn't display on stdout
        """
        if kerberos_dir is None:
            if os.name == 'nt':
                abs_dir = '%LocalAppData%\\lsassy\\tickets'
            else:
                abs_dir = os.path.expanduser('~') + '/.config/lsassy/tickets'
        else:
            if len(self._tickets) == 0 and not quiet:
                lsassy_logger.warning("No kerberos tickets found")
                return True
            abs_dir = os.path.abspath(kerberos_dir)

        if len(self._tickets) > 0:
            if not os.path.exists(abs_dir):
                try:
                    os.makedirs(abs_dir)
                except Exception as e:
                    lsassy_logger.warning("Cannot create %s for saving kerberos tickets" % abs_dir, exc_info=True)
                    return True
            for ticket in self._tickets:
                for filename in ticket.kirbi_data:
                    # Trick to add expiration date in ticket filename "YEAR MONTH DAY HOUR MINUTE SECOND"
                    with open(os.path.join(abs_dir, filename.split(".kirbi")[0] + '_' + ticket.EndTime.strftime('%Y%m%d%H%M%S') + ".kirbi"), 'wb') as f:
                        f.write(ticket.kirbi_data[filename].dump())
            if not quiet:
                if len(self._tickets) > 1:
                    print("%s Kerberos tickets written to %s" % (len(self._tickets),abs_dir))
                else:
                    print("%s Kerberos ticket written to %s" % (len(self._tickets),abs_dir))

        return True
    
    def write_masterkeys(self, masterkeys_file=None, quiet=False):
        """
        Output masterkeys to file
        :param masterkeys_file: Output file
        :param quiet: If set, doesn't display on stdout
        """
        if masterkeys_file is None:
            if os.name == 'nt':
                abs_dir = '%LocalAppData%\\lsassy\\masterkeys.txt'
            else:
                abs_dir = os.path.expanduser('~') + '/.config/lsassy/masterkeys.txt'
        else:
            if len(self._masterkeys) == 0 and not quiet:
                lsassy_logger.warning("No DPAPI masterkey found")
                return True
            abs_dir = os.path.abspath(masterkeys_file)

        if len(self._masterkeys) == 0:
            if not quiet:
                lsassy_logger.warning("No masterkey found")
            return True
        with open(abs_dir,'a+') as file:
            for mk in self._masterkeys:
                file.write(mk+'\n')
        if not quiet:
            print("{} masterkeys saved to {}".format(len(self._masterkeys), abs_dir))
        return True
